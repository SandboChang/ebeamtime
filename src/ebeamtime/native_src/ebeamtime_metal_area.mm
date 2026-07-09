#import <Foundation/Foundation.h>
#import <Metal/Metal.h>

#include <cstdint>
#include <cstring>
#include <string>

static thread_local std::string g_last_error;

static void set_ns_error(NSString* context, NSError* error) {
    NSString* message = error ? [error localizedDescription] : @"unknown Metal error";
    g_last_error = std::string([context UTF8String]) + ": " + [message UTF8String];
}

extern "C" const char* ebeamtime_metal_last_error() {
    return g_last_error.c_str();
}

extern "C" int ebeamtime_metal_available() {
    @autoreleasepool {
        id<MTLDevice> device = MTLCreateSystemDefaultDevice();
        return device ? 1 : 0;
    }
}

static NSString* metal_source() {
    static const char* source = R"METAL(
#include <metal_stdlib>
using namespace metal;

kernel void area_totals_kernel(
    device const long* vertices_xy [[buffer(0)]],
    device const ulong* offsets [[buffer(1)]],
    device const int* exposure_ids [[buffer(2)]],
    device ulong* polygon_twice_areas [[buffer(3)]],
    device uchar* zero_flags [[buffer(4)]],
    constant ulong& polygon_count [[buffer(5)]],
    constant uint& exposure_count [[buffer(6)]],
    uint gid [[thread_position_in_grid]]
) {
    if ((ulong)gid >= polygon_count) {
        return;
    }
    int exposure_id = exposure_ids[gid];
    if (exposure_id < 0 || (uint)exposure_id >= exposure_count) {
        polygon_twice_areas[gid] = 0;
        zero_flags[gid] = 0;
        return;
    }
    ulong start = offsets[gid];
    ulong end = offsets[gid + 1];
    if (end <= start + 2) {
        polygon_twice_areas[gid] = 0;
        zero_flags[gid] = 1;
        return;
    }
    long twice_area_signed = 0;
    for (ulong cursor = start; cursor < end; ++cursor) {
        ulong next = cursor + 1 == end ? start : cursor + 1;
        long x0 = vertices_xy[cursor * 2];
        long y0 = vertices_xy[cursor * 2 + 1];
        long x1 = vertices_xy[next * 2];
        long y1 = vertices_xy[next * 2 + 1];
        twice_area_signed += x0 * y1 - x1 * y0;
    }
    ulong twice_area = twice_area_signed < 0 ? (ulong)(-twice_area_signed) : (ulong)twice_area_signed;
    polygon_twice_areas[gid] = twice_area;
    zero_flags[gid] = twice_area == 0 ? 1 : 0;
}
)METAL";
    return [NSString stringWithUTF8String:source];
}

extern "C" int ebeamtime_metal_area_totals(
    const long long* vertices_xy,
    const unsigned long long* offsets,
    const int* exposure_ids,
    unsigned long long polygon_count,
    unsigned int exposure_count,
    unsigned long long* twice_areas_out,
    unsigned long long* counts_out,
    unsigned long long* zero_area_count_out,
    float* elapsed_ms_out
) {
    if (!vertices_xy || !offsets || !exposure_ids || !twice_areas_out || !counts_out || !zero_area_count_out || !elapsed_ms_out) {
        g_last_error = "null pointer passed to ebeamtime_metal_area_totals";
        return 1;
    }
    std::memset(twice_areas_out, 0, sizeof(unsigned long long) * exposure_count);
    std::memset(counts_out, 0, sizeof(unsigned long long) * exposure_count);
    *zero_area_count_out = 0;
    *elapsed_ms_out = 0.0f;
    if (polygon_count == 0 || exposure_count == 0) {
        return 0;
    }

    @autoreleasepool {
        id<MTLDevice> device = MTLCreateSystemDefaultDevice();
        if (!device) {
            g_last_error = "no Metal device available";
            return 1;
        }
        NSError* error = nil;
        id<MTLLibrary> library = [device newLibraryWithSource:metal_source() options:nil error:&error];
        if (!library) {
            set_ns_error(@"newLibraryWithSource", error);
            return 1;
        }
        id<MTLFunction> function = [library newFunctionWithName:@"area_totals_kernel"];
        if (!function) {
            g_last_error = "Metal function area_totals_kernel not found";
            return 1;
        }
        id<MTLComputePipelineState> pipeline = [device newComputePipelineStateWithFunction:function error:&error];
        if (!pipeline) {
            set_ns_error(@"newComputePipelineStateWithFunction", error);
            return 1;
        }

        unsigned long long vertex_scalar_count = offsets[polygon_count] * 2ULL;
        id<MTLBuffer> vertices_buffer = [device newBufferWithBytes:vertices_xy length:sizeof(long long) * vertex_scalar_count options:MTLResourceStorageModeShared];
        id<MTLBuffer> offsets_buffer = [device newBufferWithBytes:offsets length:sizeof(unsigned long long) * (polygon_count + 1ULL) options:MTLResourceStorageModeShared];
        id<MTLBuffer> exposure_buffer = [device newBufferWithBytes:exposure_ids length:sizeof(int) * polygon_count options:MTLResourceStorageModeShared];
        id<MTLBuffer> polygon_area_buffer = [device newBufferWithLength:sizeof(unsigned long long) * polygon_count options:MTLResourceStorageModeShared];
        id<MTLBuffer> zero_flags_buffer = [device newBufferWithLength:sizeof(std::uint8_t) * polygon_count options:MTLResourceStorageModeShared];
        id<MTLBuffer> polygon_count_buffer = [device newBufferWithBytes:&polygon_count length:sizeof(unsigned long long) options:MTLResourceStorageModeShared];
        id<MTLBuffer> exposure_count_buffer = [device newBufferWithBytes:&exposure_count length:sizeof(unsigned int) options:MTLResourceStorageModeShared];
        if (!vertices_buffer || !offsets_buffer || !exposure_buffer || !polygon_area_buffer || !zero_flags_buffer || !polygon_count_buffer || !exposure_count_buffer) {
            g_last_error = "failed to allocate Metal buffers";
            return 1;
        }

        id<MTLCommandQueue> queue = [device newCommandQueue];
        id<MTLCommandBuffer> command = [queue commandBuffer];
        id<MTLComputeCommandEncoder> encoder = [command computeCommandEncoder];
        [encoder setComputePipelineState:pipeline];
        [encoder setBuffer:vertices_buffer offset:0 atIndex:0];
        [encoder setBuffer:offsets_buffer offset:0 atIndex:1];
        [encoder setBuffer:exposure_buffer offset:0 atIndex:2];
        [encoder setBuffer:polygon_area_buffer offset:0 atIndex:3];
        [encoder setBuffer:zero_flags_buffer offset:0 atIndex:4];
        [encoder setBuffer:polygon_count_buffer offset:0 atIndex:5];
        [encoder setBuffer:exposure_count_buffer offset:0 atIndex:6];
        NSUInteger threads = pipeline.maxTotalThreadsPerThreadgroup;
        if (threads > 256) {
            threads = 256;
        }
        MTLSize grid = MTLSizeMake((NSUInteger)polygon_count, 1, 1);
        MTLSize group = MTLSizeMake(threads, 1, 1);
        NSTimeInterval start = [NSDate timeIntervalSinceReferenceDate];
        [encoder dispatchThreads:grid threadsPerThreadgroup:group];
        [encoder endEncoding];
        [command commit];
        [command waitUntilCompleted];
        NSTimeInterval stop = [NSDate timeIntervalSinceReferenceDate];
        if (command.status == MTLCommandBufferStatusError) {
            set_ns_error(@"Metal command buffer", command.error);
            return 1;
        }
        *elapsed_ms_out = (float)((stop - start) * 1000.0);

        auto* polygon_areas = static_cast<unsigned long long*>([polygon_area_buffer contents]);
        auto* zero_flags = static_cast<std::uint8_t*>([zero_flags_buffer contents]);
        for (unsigned long long index = 0; index < polygon_count; ++index) {
            int exposure_id = exposure_ids[index];
            if (exposure_id < 0 || static_cast<unsigned int>(exposure_id) >= exposure_count) {
                continue;
            }
            counts_out[exposure_id] += 1ULL;
            twice_areas_out[exposure_id] += polygon_areas[index];
            if (zero_flags[index]) {
                *zero_area_count_out += 1ULL;
            }
        }
        g_last_error.clear();
        return 0;
    }
}
