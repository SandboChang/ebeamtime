#include <cuda_runtime.h>

#include <cstdint>
#include <cstring>
#include <string>

static thread_local std::string g_last_error;

static int set_error(const char* context, cudaError_t status) {
    g_last_error = std::string(context) + ": " + cudaGetErrorString(status);
    return 1;
}

extern "C" const char* ebeamtime_cuda_last_error() {
    return g_last_error.c_str();
}

extern "C" int ebeamtime_cuda_available() {
    int count = 0;
    cudaError_t status = cudaGetDeviceCount(&count);
    if (status != cudaSuccess) {
        g_last_error = cudaGetErrorString(status);
        return 0;
    }
    return count > 0 ? 1 : 0;
}

extern "C" int ebeamtime_cuda_release_device_memory() {
    cudaError_t status = cudaDeviceSynchronize();
    if (status != cudaSuccess) {
        return set_error("cudaDeviceSynchronize", status);
    }
    return 0;
}

__global__ void area_totals_kernel(
    const long long* vertices_xy,
    const unsigned long long* offsets,
    const int* exposure_ids,
    unsigned long long polygon_count,
    unsigned int exposure_count,
    unsigned long long* twice_areas,
    unsigned long long* counts,
    unsigned long long* zero_area_count
) {
    unsigned long long index = blockIdx.x * blockDim.x + threadIdx.x;
    unsigned long long stride = blockDim.x * gridDim.x;
    for (; index < polygon_count; index += stride) {
        int exposure_id = exposure_ids[index];
        if (exposure_id < 0 || static_cast<unsigned int>(exposure_id) >= exposure_count) {
            continue;
        }
        atomicAdd(&counts[exposure_id], 1ULL);
        unsigned long long start = offsets[index];
        unsigned long long end = offsets[index + 1];
        if (end <= start + 2) {
            atomicAdd(zero_area_count, 1ULL);
            continue;
        }
        long long twice_area_signed = 0;
        for (unsigned long long cursor = start; cursor < end; ++cursor) {
            unsigned long long next = cursor + 1 == end ? start : cursor + 1;
            long long x0 = vertices_xy[cursor * 2];
            long long y0 = vertices_xy[cursor * 2 + 1];
            long long x1 = vertices_xy[next * 2];
            long long y1 = vertices_xy[next * 2 + 1];
            twice_area_signed += x0 * y1 - x1 * y0;
        }
        unsigned long long twice_area = twice_area_signed < 0
            ? static_cast<unsigned long long>(-twice_area_signed)
            : static_cast<unsigned long long>(twice_area_signed);
        if (twice_area == 0) {
            atomicAdd(zero_area_count, 1ULL);
        }
        atomicAdd(&twice_areas[exposure_id], twice_area);
    }
}

extern "C" int ebeamtime_cuda_area_totals(
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
        g_last_error = "null pointer passed to ebeamtime_cuda_area_totals";
        return 1;
    }
    *zero_area_count_out = 0;
    *elapsed_ms_out = 0.0f;
    std::memset(twice_areas_out, 0, sizeof(unsigned long long) * exposure_count);
    std::memset(counts_out, 0, sizeof(unsigned long long) * exposure_count);
    if (polygon_count == 0 || exposure_count == 0) {
        return 0;
    }

    long long* d_vertices = nullptr;
    unsigned long long* d_offsets = nullptr;
    int* d_exposure_ids = nullptr;
    unsigned long long* d_twice_areas = nullptr;
    unsigned long long* d_counts = nullptr;
    unsigned long long* d_zero_area_count = nullptr;
    cudaEvent_t start_event = nullptr;
    cudaEvent_t stop_event = nullptr;
    int status_code = 1;
    int block_size = 256;
    int grid_size = static_cast<int>((polygon_count + block_size - 1ULL) / block_size);
    if (grid_size < 1) {
        grid_size = 1;
    } else if (grid_size > 4096) {
        grid_size = 4096;
    }

    unsigned long long vertex_scalar_count = offsets[polygon_count] * 2ULL;
    cudaError_t status = cudaMalloc(&d_vertices, sizeof(long long) * vertex_scalar_count);
    if (status != cudaSuccess) { set_error("cudaMalloc vertices", status); goto cleanup; }
    status = cudaMalloc(&d_offsets, sizeof(unsigned long long) * (polygon_count + 1ULL));
    if (status != cudaSuccess) { set_error("cudaMalloc offsets", status); goto cleanup; }
    status = cudaMalloc(&d_exposure_ids, sizeof(int) * polygon_count);
    if (status != cudaSuccess) { set_error("cudaMalloc exposure_ids", status); goto cleanup; }
    status = cudaMalloc(&d_twice_areas, sizeof(unsigned long long) * exposure_count);
    if (status != cudaSuccess) { set_error("cudaMalloc twice_areas", status); goto cleanup; }
    status = cudaMalloc(&d_counts, sizeof(unsigned long long) * exposure_count);
    if (status != cudaSuccess) { set_error("cudaMalloc counts", status); goto cleanup; }
    status = cudaMalloc(&d_zero_area_count, sizeof(unsigned long long));
    if (status != cudaSuccess) { set_error("cudaMalloc zero count", status); goto cleanup; }

    status = cudaMemcpy(d_vertices, vertices_xy, sizeof(long long) * vertex_scalar_count, cudaMemcpyHostToDevice);
    if (status != cudaSuccess) { set_error("cudaMemcpy vertices", status); goto cleanup; }
    status = cudaMemcpy(d_offsets, offsets, sizeof(unsigned long long) * (polygon_count + 1ULL), cudaMemcpyHostToDevice);
    if (status != cudaSuccess) { set_error("cudaMemcpy offsets", status); goto cleanup; }
    status = cudaMemcpy(d_exposure_ids, exposure_ids, sizeof(int) * polygon_count, cudaMemcpyHostToDevice);
    if (status != cudaSuccess) { set_error("cudaMemcpy exposure_ids", status); goto cleanup; }
    status = cudaMemset(d_twice_areas, 0, sizeof(unsigned long long) * exposure_count);
    if (status != cudaSuccess) { set_error("cudaMemset twice_areas", status); goto cleanup; }
    status = cudaMemset(d_counts, 0, sizeof(unsigned long long) * exposure_count);
    if (status != cudaSuccess) { set_error("cudaMemset counts", status); goto cleanup; }
    status = cudaMemset(d_zero_area_count, 0, sizeof(unsigned long long));
    if (status != cudaSuccess) { set_error("cudaMemset zero count", status); goto cleanup; }

    status = cudaEventCreate(&start_event);
    if (status != cudaSuccess) { set_error("cudaEventCreate start", status); goto cleanup; }
    status = cudaEventCreate(&stop_event);
    if (status != cudaSuccess) { set_error("cudaEventCreate stop", status); goto cleanup; }
    status = cudaEventRecord(start_event);
    if (status != cudaSuccess) { set_error("cudaEventRecord start", status); goto cleanup; }

    area_totals_kernel<<<grid_size, block_size>>>(
        d_vertices,
        d_offsets,
        d_exposure_ids,
        polygon_count,
        exposure_count,
        d_twice_areas,
        d_counts,
        d_zero_area_count
    );
    status = cudaGetLastError();
    if (status != cudaSuccess) { set_error("area_totals_kernel", status); goto cleanup; }
    status = cudaEventRecord(stop_event);
    if (status != cudaSuccess) { set_error("cudaEventRecord stop", status); goto cleanup; }
    status = cudaEventSynchronize(stop_event);
    if (status != cudaSuccess) { set_error("cudaEventSynchronize", status); goto cleanup; }
    status = cudaEventElapsedTime(elapsed_ms_out, start_event, stop_event);
    if (status != cudaSuccess) { set_error("cudaEventElapsedTime", status); goto cleanup; }

    status = cudaMemcpy(twice_areas_out, d_twice_areas, sizeof(unsigned long long) * exposure_count, cudaMemcpyDeviceToHost);
    if (status != cudaSuccess) { set_error("cudaMemcpy twice_areas", status); goto cleanup; }
    status = cudaMemcpy(counts_out, d_counts, sizeof(unsigned long long) * exposure_count, cudaMemcpyDeviceToHost);
    if (status != cudaSuccess) { set_error("cudaMemcpy counts", status); goto cleanup; }
    status = cudaMemcpy(zero_area_count_out, d_zero_area_count, sizeof(unsigned long long), cudaMemcpyDeviceToHost);
    if (status != cudaSuccess) { set_error("cudaMemcpy zero count", status); goto cleanup; }
    g_last_error.clear();
    status_code = 0;

cleanup:
    if (start_event) { cudaEventDestroy(start_event); }
    if (stop_event) { cudaEventDestroy(stop_event); }
    if (d_vertices) { cudaFree(d_vertices); }
    if (d_offsets) { cudaFree(d_offsets); }
    if (d_exposure_ids) { cudaFree(d_exposure_ids); }
    if (d_twice_areas) { cudaFree(d_twice_areas); }
    if (d_counts) { cudaFree(d_counts); }
    if (d_zero_area_count) { cudaFree(d_zero_area_count); }
    return status_code;
}
