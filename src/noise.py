def value_noise_2d(x: int, y: int, scale: float, seed: int) -> float:
    def corner_val(xi: int, yi: int) -> float:
        n = xi * 1619 + yi * 31337 + seed * 1013904223
        n = (n ^ (n >> 8)) & 0xFFFFFFFF
        return (n & 0xFFFF) / 0xFFFF

    fx = x / scale
    fy = y / scale
    xi, yi = int(fx), int(fy)
    tx = fx - xi
    ty = fy - yi
    tx = tx * tx * (3 - 2 * tx)
    ty = ty * ty * (3 - 2 * ty)
    v00 = corner_val(xi, yi)
    v10 = corner_val(xi + 1, yi)
    v01 = corner_val(xi, yi + 1)
    v11 = corner_val(xi + 1, yi + 1)
    return (
        v00 * (1 - tx) * (1 - ty)
        + v10 * tx * (1 - ty)
        + v01 * (1 - tx) * ty
        + v11 * tx * ty
    )
