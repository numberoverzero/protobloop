import copy
from typing import Any, Union
from typing import Type as PyType
from bloop import BaseModel, Column
from bloop.models import IMeta, subclassof, instanceof, bind_column
from bloop.types import String, Type

__all__ = ["mapper", "shared_base"]

ModelCls = PyType[BaseModel]
TypeDef = Union[PyType[Type], Type]
ColumnRef = Union[Column, str]


def shared_base(hk_name="hk", rk_name="rk", base: ModelCls=BaseModel) -> ModelCls:
    class SharedBase(base):
        class Meta(IMeta):
            abstract = True
        def __init_subclass__(cls: type, **kwargs):
            super().__init_subclass__(**kwargs)
            cls.Meta.table_name = SharedBase.Meta.table_name
    bind_column(SharedBase, hk_name, Column(String, hash_key=True, dynamo_name=hk_name), force=True)
    bind_column(SharedBase, rk_name, Column(String, range_key=True, dynamo_name=rk_name), force=True)
    SharedBase.Meta.abstract = False
    return SharedBase


def mapper(model: ModelCls) -> "Mapper":
    return Mapper(model)


class Mapper:
    model: ModelCls

    def __init__(self, model: ModelCls) -> None:
        self.model = model

    def prefix(self, typedef: TypeDef, column: ColumnRef, prefix: str) -> Column:
        column = _clone_column(self.model, column)
        column.typedef = PrefixType(typedef, prefix)
        return column

    def static(self, typedef: TypeDef, column: ColumnRef, value: Any) -> Column:
        column = _clone_column(self.model, column)
        column.typedef = StaticType(typedef, value)
        column.default = lambda: value
        return column

    def override(self, typedef: TypeDef, column: ColumnRef) -> Column:
        column = _clone_column(self.model, column)
        column.typedef = _type_instance(typedef)
        return column


class StaticType(String):
    _wrapped: Type
    _value: Any

    def __init__(self, wrapped: TypeDef, value: Any) -> None:
        self._value = value
        self._wrapped = _type_instance(wrapped)
        self.python_type = self._wrapped.python_type

    def dynamo_dump(self, value, *, context, **kwargs):
        if (value != self._value) and (value is not None):
            raise ValueError(f"tried to dump unexpected value '{value}' instead of static '{self._value}'")
        return self._wrapped.dynamo_dump(value, context=context, **kwargs)

    def dynamo_load(self, value, *, context, **kwargs):
        value = self._wrapped.dynamo_load(value, context=context, **kwargs)
        if value != self._value:
            raise ValueError(f"tried to load unexpected value '{value}' instead of static '{self._value}'")
        return value

class PrefixType(String):
    _wrapped: Type
    _prefix: str

    def __init__(self, wrapped: TypeDef, prefix: str) -> None:
        self._prefix = prefix
        self._wrapped = _type_instance(wrapped)
        self.python_type = self._wrapped.python_type

    def dynamo_dump(self, value, *, context, **kwargs):
        value = self._wrapped.dynamo_dump(value, context=context, **kwargs)
        if value is not None:
            value = f"{self._prefix}{value}"
        return value

    def dynamo_load(self, value, *, context, **kwargs):
        try:
            if value is not None:
                (_prefix, value) = value.split(self._prefix, 1)
        except ValueError as err:
            raise ValueError(f"malformed value '{value}' missing prefix '{self._prefix}'") from err
        return self._wrapped.dynamo_load(value, context=context, **kwargs)


def _type_instance(typedef: TypeDef) -> Type:
    if subclassof(typedef, Type):
        typedef = typedef()
    if instanceof(typedef, Type):
        return typedef
    else:
        raise TypeError(f"Expected {typedef} to be instance or subclass of bloop.Type")


def _clone_column(model: ModelCls, column: ColumnRef) -> Column:
    if isinstance(column, str):
        column = model.Meta.columns_by_name[column]
    clone = copy.copy(column)
    # pin to the original dynamo_name so that we replace it
    clone._dynamo_name = column.dynamo_name
    return clone
