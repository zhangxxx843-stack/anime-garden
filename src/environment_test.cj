package miniproject

import std.unittest.*
import std.unittest.testmacro.*

// 验证培训涉及的语法和单元测试工具链，后续另加实际业务的测试。
@Test
class EnvironmentTest {
    @TestCase
    func pipelinePassesValues(): Unit {
        let plusOne = { value: Int64 => value + 1 }
        let twice = { value: Int64 => value * 2 }
        let actual = 4 |> plusOne |> twice
        @Expect(actual, 10)
    }

    @TestCase
    func optionHandlesPresentAndMissingValues(): Unit {
        let cases: Array<(Option<Int64>, Int64)> = [(Some(7), 7), (None, 0)]
        for ((input, expected) in cases) {
            let actual = match (input) {
                case Some(value) => value
                case None => 0
            }
            @Expect(actual, expected)
        }
    }

    @TestCase
    func exceptionPreservesMessage(): Unit {
        var actual = ""
        try {
            throw Exception("environment check")
        } catch (error: Exception) {
            actual = error.message
        }
        @Expect(actual, "environment check")
    }
}
