from types import SimpleNamespace
from enum import Enum

class Display:
    BLUE    = (255, 0, 0)
    LIME    = (0, 255, 0)
    GREEN   = (50, 200, 50)
    RED     = (0, 0, 255)
    YELLOW  = (0, 255, 255)
    CYAN    = (255, 255, 0)
    MAGENTA = (255, 0, 255)
    ORANGE  = (0, 165, 255)
    PURPLE  = (128, 0, 128)
    PINK    = (203, 192, 255)
    BROWN   = (42, 42, 165)
    GREY    = (128, 128, 128)
    WHITE   = (255, 255, 255)
    BLACK   = (0, 0, 0)

# State class for different sequence states and colours.
class State(Enum):
    IDLE     = (0, Display.WHITE)
    REACHING = (1, Display.WHITE)
    SELECTED  = (2, Display.GREY)
    GRABBED  = (3, Display.LIME)
    PULLING = (4, Display.YELLOW)
    DRAGGING   = (5, Display.GREEN)
    DROPPED  = (6, Display.RED)

    @property
    def color(self):
        return self.value[1]

    @property
    def code(self):
        return self.value[0]


class Hand:
    WRIST = 0
    Thumb = SimpleNamespace(BASE=1, PIP=2, DIP=3, TIP=4)
    Index = SimpleNamespace(BASE=5, PIP=6, DIP=7, TIP=8)
    Middle = SimpleNamespace(BASE=9, PIP=10, DIP=11, TIP=12)
    Ring = SimpleNamespace(BASE=13, PIP=14, DIP=15, TIP=16)
    Pinky = SimpleNamespace(BASE=17, PIP=18, DIP=19, TIP=20)

    @classmethod
    def indices(cls):
        return [cls.WRIST] + [v for finger in [cls.Thumb, cls.Index, cls.Middle, cls.Ring, cls.Pinky] for v in vars(finger).values()]

class Eye:
    class Left:
        UpperLid = SimpleNamespace(OUTER=33, LATERAL=161, MID=159, MEDIAL=157, INNER=133)
        LowerLid = SimpleNamespace(OUTER=7, LATERAL=163, MID=145, MEDIAL=153, INNER=155)
        Iris = SimpleNamespace(INNER=469, OUTER=471, UPPER=470, LOWER=472)
    class Right:
        UpperLid = SimpleNamespace(OUTER=263, LATERAL=388, MID=386, MEDIAL=384, INNER=362)
        LowerLid = SimpleNamespace(OUTER=249, LATERAL=390, MID=374, MEDIAL=380, INNER=382)
        Iris = SimpleNamespace(INNER=476, OUTER=474, UPPER=475, LOWER=477)

    @classmethod
    def indices(cls):
        return [v for eye in [cls.Left, cls.Right] for part in [eye.UpperLid, eye.LowerLid, eye.Iris] for v in vars(part).values()]

class Nose:
    BASE = 2
    TIP = 4
    BRIDGE = 195
    RADIX = 168
    LEFT = 98
    RIGHT = 327

    @classmethod
    def indices(cls):
        return [cls.BASE, cls.TIP, cls.BRIDGE, cls.RADIX, cls.LEFT, cls.RIGHT]


class Mouth:
    OUTER = SimpleNamespace(UPPER=[61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291],
                            LOWER=[146, 91, 181, 84, 17, 314, 405, 321, 375, 291])
    INNER = SimpleNamespace(UPPER=[78, 95, 88, 178, 87, 14, 317, 402, 318, 324],
                            LOWER=[308, 415, 310, 311, 312, 13, 82, 81, 80, 191])


    @classmethod
    def indices(cls):
        return [v for part in [cls.OUTER, cls.INNER] for side in [part.UPPER, part.LOWER] for v in side]
