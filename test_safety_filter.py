import sys
import os

# Insert workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from footybitez.media.media_sourcer import MediaSourcer

def test_safety_filter():
    sourcer = MediaSourcer()

    # Test cases that SHOULD be rejected (return True)
    assert sourcer._is_bad_image(url="https://thumb-nss.xhcdn.com/a/cHzGchsI19DieX3NdwVgJQ/016/534/148/2560x1440.3.webp"), "Should reject adult CDN domain"
    assert sourcer._is_bad_image(url="http://xhamster.com/video/1234"), "Should reject xhamster domain"
    assert sourcer._is_bad_image(title="Crazy football moments sex scene"), "Should reject title containing adult keyword 'sex'"
    assert sourcer._is_bad_image(tags="porn soccer fans"), "Should reject tags containing 'porn'"
    assert sourcer._is_bad_image(title="nfl touchdown giants"), "Should reject American football keywords"
    assert sourcer._is_bad_image(title="England women team celebrating"), "Should reject female football keywords"

    # Test cases that SHOULD NOT be rejected (return False)
    assert not sourcer._is_bad_image(url="https://upload.wikimedia.org/wikipedia/commons/c/cf/Bernardo_Silva.png"), "Should accept normal Wikipedia URL"
    assert not sourcer._is_bad_image(title="Real Madrid confirm Bernardo Silva signing", tags="soccer men football"), "Should accept normal title and tags"
    assert not sourcer._is_bad_image(title="Manchester United home strip", tags="jersey kit"), "Should accept 'strip' in soccer context (e.g. uniform)"
    assert not sourcer._is_bad_image(title="Tactical assessment of team formation"), "Should accept 'assessment' containing 'ass'"

    print("All safety filter unit tests passed successfully!")

if __name__ == "__main__":
    test_safety_filter()
