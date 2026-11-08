package miniproject

import std.fs.*
import std.unittest.*
import std.unittest.testmacro.*

@Test
class CommandProtocolTest {
    @TestCase
    func initializesAndReturnsSnapshot(): Unit {
        let path = "data/protocol-test.tsv"
        removeIfExists(path, recursive: false)
        let initResponse = executeCommand(["init"], path)
        @Expect(initResponse.startsWith("OK"), true)
        let snapshot = executeCommand(["snapshot"], path)
        @Expect(snapshot.contains("category-food"), true)
        @Expect(snapshot.contains("餐饮"), true)
        removeIfExists(path, recursive: false)
    }
}
