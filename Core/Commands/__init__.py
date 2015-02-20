import glob
import os

extra_commands = glob.glob("Core" + os.sep + "Commands" + os.sep + "*.py")
__all__ = [os.path.basename(f)[:-3] for f in extra_commands]