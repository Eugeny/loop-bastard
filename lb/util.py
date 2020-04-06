NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
NOTES_IN_OCTAVE = len(NOTES)


def number_to_note(number: int):
    octave = number // NOTES_IN_OCTAVE - 1
    note = NOTES[number % NOTES_IN_OCTAVE]
    return note, octave


def list_next(lst, item):
    if not len(lst):
        return None
    if item not in lst:
        return lst[0]
    i = lst.index(item)
    i = min(len(lst) - 1, i + 1)
    return lst[i]


def list_prev(lst, item):
    if not len(lst):
        return None
    if item not in lst:
        return lst[0]
    i = lst.index(item)
    i = max(0, i - 1)
    return lst[i]
