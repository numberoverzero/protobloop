from uuid import uuid4
from bloop import String, UUID
from protobloop import mapper, shared_base


b = shared_base("h", "r")
m = mapper(b)


class User(b):
    _p = m.static(String, "h", "users")
    id = m.prefix(UUID, b.r, "uById::")


from bloop import Engine
from bloop.models import unpack_from_dynamodb
from bloop.util import dump_key
engine = Engine()
engine.bind(b, skip_table_setup=True)

user = User(id=uuid4())
print(user)
print(dump_key(engine, user))
print(unpack_from_dynamodb(
    attrs=dump_key(engine, user),
    expected=User.Meta.columns,
    model=User,
    engine=engine
))