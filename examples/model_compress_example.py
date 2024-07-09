import torch
import torchvision.models as models
import cuda_float_compress
import zstandard as zstd
import numpy as np

# Function to compress a tensor using Zstd
def compress_tensor_zstd(tensor, compression_level=1):
    # Convert tensor to bytes
    tensor_bytes = tensor.cpu().numpy().tobytes()
    
    # Create a Zstd compressor
    cctx = zstd.ZstdCompressor(level=compression_level)
    
    # Compress the tensor bytes
    compressed_data = cctx.compress(tensor_bytes)
    
    return compressed_data

# Function to decompress Zstd compressed data back to a tensor
def decompress_tensor_zstd(compressed_data, expected_bytes):
    # Create a Zstd decompressor
    dctx = zstd.ZstdDecompressor()
    
    # Decompress the data
    decompressed_bytes = dctx.decompress(compressed_data)

    if len(decompressed_bytes) != expected_bytes:
        return None

    tensor = torch.tensor(np.frombuffer(decompressed_bytes, dtype=np.uint8))

    return tensor

def main():
    # Load a pretrained model (e.g., ResNet18)
    model = models.resnet18(pretrained=True)

    # Verify decompression
    original_params = torch.cat([p.data.view(-1) for p in model.parameters()])
    print(f"oring_params.shape: {original_params.shape}")
    for p in model.parameters():
        data = p.data.view(-1)

        (d_min, d_max) = torch.aminmax(data.detach())
        range = (d_max - d_min).float()
        rescaled = (data - d_min).float() / range

        raw_data = rescaled

        print(f"raw_data = {raw_data} {raw_data.shape} {raw_data.dtype} {raw_data.device}")

        # Set error bound for compression (adjust as needed)
        error_bound = 0.00001

        compressed_params = cuda_float_compress.cuszplus_compress(raw_data, error_bound)

        print(f"compressed_params = {compressed_params} {compressed_params.shape} {compressed_params.dtype} {compressed_params.device}")

        decompressed_params = cuda_float_compress.cuszplus_decompress(compressed_params)

        print(f"decompressed_params = {decompressed_params} {decompressed_params.shape} {decompressed_params.dtype} {decompressed_params.device}")

        mse = torch.mean((raw_data - decompressed_params) ** 2)
        ratio = raw_data.numel() * 4.0 / compressed_params.numel()
        print(f"Mean Squared Error after compression/decompression: {mse.item()} Ratio: {ratio:.2f}")

if __name__ == "__main__":
    main()
