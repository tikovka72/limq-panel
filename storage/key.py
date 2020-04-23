#   _        _   _     _       _                       __  __  ____
#  | |      (_) | |   | |     (_)                     |  \/  |/ __ \
#  | |       _  | |_  | |__    _   _   _   _ __ ___   | \  / | |  | |
#  | |      | | | __| | "_ \  | | | | | | | "_ ` _ \  | |\/| | |  | |
#  | |____  | | | |_  | | | | | | | |_| | | | | | | | | |  | | |__| |
#  |______| |_|  \__| |_| |_| |_|  \__,_| |_| |_| |_| |_|  |_|\___\_\


import sqlalchemy
from .db_session import ModelBase

from .channel import Channel


class Key(ModelBase):
    """
    SqlAlchemy-integrated access key descriptor.
    """

    __tablename__ = "keys"

    READ = 1 << 0
    WRITE = 1 << 1
    PAUSED = 1 << 8

    key = sqlalchemy.Column(sqlalchemy.String(length=32), nullable=False, primary_key=True,
                            unique=True)
    name = sqlalchemy.Column(sqlalchemy.String(length=20), nullable=True, unique=False)
    chan_id = sqlalchemy.Column(sqlalchemy.String(length=64), sqlalchemy.ForeignKey(Channel.id),
                                nullable=False)
    perm = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=0)

    def can_read(self) -> bool:
        return self.perm & self.READ != 0

    def can_write(self) -> bool:
        return self.perm & self.WRITE != 0

    def bidirectional(self) -> bool:
        return self.perm & self.WRITE & self.READ != 0

    def active(self) -> bool:
        return self.perm & self.PAUSED == 0

    def toggle_active(self) -> bool:
        self.perm ^= self.PAUSED

        return self.active()

