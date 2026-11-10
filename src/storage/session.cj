package xin_xuan_glass_probe.storage

@When[os == "Windows"]
import std.env.getVariable
@When[os == "Windows"]
import std.fs.Path

/** No program-directory fallback: moving the EXE must not change the user's data location. */
@When[os == "Windows"]
public func defaultDataRoot(): String {
    let base = getVariable("LOCALAPPDATA").getOrThrow({=> IllegalArgumentException("无法获取当前账户的应用数据目录。")})
    if (base.isEmpty() || !Path(base).isAbsolute()) { throw IllegalArgumentException("账户应用数据目录无效。") }
    Path(base).join(Path("XinXuanShopping")).normalize().toString()
}

@When[os != "Windows"]
public func defaultDataRoot(): String {
    throw IllegalArgumentException("正式应用仅面向 Windows；宿主测试请指定临时数据目录。")
}

/** State updates survive failed writes. The UI binds unsaved/message and never auto-opens rating. */
public class ShoppingSession {
    private let store: LocalStore
    private var current = ShoppingState(None, [])
    private var dirty = false
    private var message = ""
    public prop unsaved: Bool { get() { dirty } }
    public prop saveMessage: String { get() { message } }
    public let restoreWarning: String
    public let restored: Bool
    public prop state: ShoppingState { get() { ShoppingState(current.budget, current.products) } }

    public init(store: LocalStore) {
        this.store = store
        let restored = store.load()
        this.restoreWarning = restored.warning
        this.restored = restored.state.isSome()
        if (let Some(value) <- restored.state) { current = value }
    }
    public func update(value: ShoppingState): Unit {
        current = ShoppingState(value.budget, value.products)
        dirty = true
        retrySave()
    }
    public func retrySave(): Unit {
        if (!dirty) { return }
        try {
            current = store.save(current)
            dirty = false
            message = "已保存在本机"
        } catch (error: Exception) {
            dirty = true
            message = "尚未保存：${error.message}。当前内容已保留，可继续操作或重试；请检查图片、磁盘空间和目录权限。"
        }
    }
}
