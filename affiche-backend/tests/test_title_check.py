import pytest

from affiche.app.mediaserver.library.title_check import matches_any, normalise, titles_differ

@pytest.mark.parametrize("server,catalogue", [
    ("Astérix & Obélix : Au service de Sa Majesté", "Astérix et Obélix: Au service de sa Majesté"),
    ("Asterix & Obelix: Au service de Sa Majeste", "Astérix & Obélix : Au service de Sa Majesté"),
    ("Divergente 3 : Au-delà du mur", "Divergente 3 - Au-delà du mur"),
    ("Cars 2: Quatre roues", "Cars 2 : Quatre roues"),
    ("A Complete Unknown", "a complete unknown"),
    ("Spider-Man: No Way Home", "Spider Man  No Way Home"),
    ("After.Life", "After Life"),
    ("W.E.", "W E"),
])
def test_two_spellings_of_the_same_title_do_not_disagree(server, catalogue):
    assert titles_differ(server, catalogue) is False

@pytest.mark.parametrize("server,catalogue", [
    ("My.movie.2012.1080p", "My Movie"),
    ("Ratatouille TRUEFRENCH DVDRip XviD VFC", "Ratatouille"),
    ("Avatar", "Avatar: The Last Airbender"),
])
def test_a_real_difference_is_reported(server, catalogue):
    assert titles_differ(server, catalogue) is True

@pytest.mark.parametrize("server,catalogue", [
    ("Anything", ""),
    ("Anything", "   "),
    ("", "Anything"),
    ("Anything", None),
    (None, "Anything"),
])
def test_a_missing_answer_is_not_a_disagreement(server, catalogue):
    assert titles_differ(server, catalogue) is False

def test_normalise_keeps_differences_that_are_real():
    assert normalise("The Matrix") != normalise("Matrix")
    assert normalise("Blade Runner") != normalise("Blade Runner 2049")
    assert normalise("Alien") != normalise("Aliens")

@pytest.mark.parametrize("other", ["Tom and Jerry", "Tom et Jerry", "Tom Jerry"])
def test_normalise_drops_the_conjunction_joining_two_names(other):
    assert normalise("Tom & Jerry") == normalise(other)

def test_normalise_collapses_whitespace_left_by_dropped_punctuation():
    assert normalise("Spider-Man: No Way Home") == "spider man no way home"

FIVE_MINARETS = [
    "Five Minarets in New York", "Act of Vengeance", "Terrorismo en Nueva York",
    "The Terrorist", "New York'ta Beş Minare", "5 Minarets à New York",
]

class TestMatchesAny:

    def test_a_release_title_other_than_the_primary_is_still_one_of_its_names(self):
        assert matches_any("Act of Vengeance", FIVE_MINARETS) is True

    def test_the_primary_matches_too(self):
        assert matches_any("Five Minarets in New York", FIVE_MINARETS) is True

    def test_spelling_is_normalised_here_as_well(self):
        assert matches_any("5 minarets a new york!", FIVE_MINARETS) is True

    def test_a_release_name_matches_none_of_them(self):
        assert matches_any("Five.Minarets.2010.1080p.WEB-DL", FIVE_MINARETS) is False

    def test_an_unrelated_title_matches_none_of_them(self):
        assert matches_any("The Matrix", FIVE_MINARETS) is False

    @pytest.mark.parametrize("candidates", [[], (), None])
    def test_nothing_to_compare_against_matches_nothing(self, candidates):
        assert matches_any("Anything", candidates) is False
