package xin_xuan_glass_probe

// Three separable box passes approximate a Gaussian blur. Work happens once at startup;
// source and blurred textures are then sampled using the same window coordinates.
func readU32(bytes: Array<UInt8>, offset: Int64): Int64 {
    Int64(bytes[offset]) + Int64(bytes[offset + 1]) * 256 +
        Int64(bytes[offset + 2]) * 65536 + Int64(bytes[offset + 3]) * 16777216
}

func blurBmp(bytes: Array<UInt8>, radius: Int64): Array<UInt8> {
    if (bytes.size < 54 || bytes[0] != 66 || bytes[1] != 77 ||
        bytes[28] != 24 || readU32(bytes, 30) != 0) {
        throw Exception("Background must be an uncompressed 24-bit BMP")
    }
    let width = readU32(bytes, 18)
    let height = readU32(bytes, 22)
    let start = readU32(bytes, 10)
    let stride = (width * 3 + 3) / 4 * 4
    if (width <= 0 || height <= 0 || width > 4096 || height > 4096 ||
        start + stride * height > bytes.size || radius < 1 || radius > 128) {
        throw Exception("Invalid background dimensions or blur radius")
    }
    var input = bytes.clone()
    let divisor = 2 * radius + 1
    for (_ in 0..3) {
        let horizontal = input.clone()
        for (y in 0..height) {
            for (channel in 0..3) {
                var sum: Int64 = 0
                for (k in -radius..radius + 1) {
                    sum += Int64(input[start + y * stride + min(width - 1, max(0, k)) * 3 + channel])
                }
                for (x in 0..width) {
                    horizontal[start + y * stride + x * 3 + channel] = UInt8(sum / divisor)
                    sum -= Int64(input[start + y * stride + max(0, x - radius) * 3 + channel])
                    sum += Int64(input[start + y * stride + min(width - 1, x + radius + 1) * 3 + channel])
                }
            }
        }
        let vertical = horizontal.clone()
        for (x in 0..width) {
            for (channel in 0..3) {
                var sum: Int64 = 0
                for (k in -radius..radius + 1) {
                    sum += Int64(horizontal[start + min(height - 1, max(0, k)) * stride + x * 3 + channel])
                }
                for (y in 0..height) {
                    vertical[start + y * stride + x * 3 + channel] = UInt8(sum / divisor)
                    sum -= Int64(horizontal[start + max(0, y - radius) * stride + x * 3 + channel])
                    sum += Int64(horizontal[start + min(height - 1, y + radius + 1) * stride + x * 3 + channel])
                }
            }
        }
        input = vertical
    }
    input
}
