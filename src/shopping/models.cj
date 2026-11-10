package xin_xuan_glass_probe.shopping

/** Input order is the product identity; equal names do not merge products. */
public struct Product {
    public let name: String
    public let price: Int64
    public let rating: ?Int64
    public let imagePath: String

    public init(name: String, price: Int64, rating: ?Int64, imagePath: String) {
        this.name = name
        this.price = price
        this.rating = rating
        this.imagePath = imagePath
    }
}

/** Score is internal ranking data; the desktop result view must not display it. */
public struct ShoppingPlan {
    public let indices: Array<Int64>
    public let totalPrice: Int64
    public let totalScore: Int64

    public init(indices: Array<Int64>, totalPrice: Int64, totalScore: Int64) {
        this.indices = indices
        this.totalPrice = totalPrice
        this.totalScore = totalScore
    }
}
