import XCTest
@testable import ShoppingGuide

final class StreamParserTests: XCTestCase {
    func testProductMarkerSplitAcrossTokensBecomesProductCardBlock() {
        var parser = StreamParser()

        XCTAssertEqual(parser.append("推荐你看 [[PRO"), [.text("推荐你看 ")])
        XCTAssertEqual(parser.append("DUCT:p_beauty_001]]"), [.productCards(["p_beauty_001"])])
        XCTAssertEqual(parser.finish(), [])
    }

    func testTrailingBracketIsHeldForNextToken() {
        var parser = StreamParser()

        XCTAssertEqual(parser.append("先看 ["), [.text("先看 ")])
        XCTAssertEqual(parser.append("[PRODUCT:p_digital_001]]"), [.productCards(["p_digital_001"])])
    }

    func testCompareMarkerProducesComparisonBlock() {
        var parser = StreamParser()

        XCTAssertEqual(
            parser.append("[[COMPARE:p_digital_001,p_digital_002]]"),
            [.comparison(["p_digital_001", "p_digital_002"])]
        )
    }

    func testFinishFlushesIncompleteMarkerAsText() {
        var parser = StreamParser()

        XCTAssertEqual(parser.append("推荐 [[PRODUCT:p_"), [.text("推荐 ")])
        XCTAssertEqual(parser.finish(), [.text("[[PRODUCT:p_")])
    }
}
