
import random

"""Defines the externally visible errors.

An RPCC server may have any number of internal errors. It must however 
catch these and convert them to ExtError instances before control
is returned to the RPCC framework. A non-ExtError error that bubbles
up into RPCC is converted into an ExtInternalError instance, and the
traceback is logged to stderr.

Base classes for your own errors:

  ExtValueError
    A value sent by the client was malformed. Examples include integers 
    outside of a specified range or strings not matching a particular
    regexp.

  ExtLookupError
    A value that was expected to represent some entity could not be
    converted to that entity. Examples include an integer that is
    expected to represent some internal object, where no object with
    the ID of the sent value actually exists.

  ExtTypeError
    For transports that define data types explicitly (XMLRPC and JSON
    for example) this error says that the wrong data type was sent.

  ExtRuntimeError
    An error has occured which does not depend on the particular values
    sent. The call might work for someone else, or if retried at a
    later time.

  ExtAccessDeniedError (an ExtRuntimeError)
    Some form of authorization failed.

  ExtTransportError
    The incoming call could not be interpreted as the protocol it was
    expected to be, an example would be XMLRPC sent to the JSON URL.
"""


class ExtError(Exception):
    # Explicit external error name for this particular subclass, if
    # any.  If set, the external error path and external error name
    # will contain .name in the subclass' place in the corresponding
    # inheritance chain, if the subclass does not have _its_own_
    # "visible" attribute set to False.
    name = ''

    # Description of error, shown in the error struct's "desc" attribute.
    desc = ''

    # If set, and .name is not set, this prefix/suffix will be removed
    # from the class name when generating the error path.
    prefix = "Ext"
    suffix = "Error"

    # Whether this exception class should be visible in the error path
    # or not. If this is False, the name will not be included in the
    # "::"-separated error path. Note that this attribute is looked up
    # locally in each class - inherited values do not count!
    visible = True

    def __init__(self, desc=None, argno=None, value=None):
        self.argno = argno
        self.traceback = []
        if hasattr(value, "get_value_string"):
            self.value = value.get_value_string()
        else:
            self.value = value
        self.id = '%06d%06d' % (random.randint(0, 1000000),
                                random.randint(0, 1000000))
        if desc:
            self.desc = desc

    def __str__(self):
        return '<ExtError %s>' % (self.name,)

    def add_traceback(self, tb):
        self.traceback = [tb] + self.traceback

    def XXXerror_name_for_class(self, cls):
        return cls.__name__

    @classmethod
    def error_path(cls):
        if cls == ExtError:
            return []

        ext_found = False
        base_path = []

        for base in cls.__bases__:
            if issubclass(base, ExtError):
                if ext_found:
                    raise ValueError(desc="Multiple bases of %s are subclasses of ExtError" % (cls.__name__,))

                ext_found = True
                base_path = base.error_path()

        if cls.__dict__.get("invisible", False):
            return base_path
        elif "name" in cls.__dict__:
            return base_path + [cls.name]
        else:
            me = cls.__name__
            if me.startswith(cls.prefix):
                me = me[len(cls.prefix):]
            return base_path + [me]

    def struct(self):
        path = self.error_path()
        return {'name': '::'.join(path),
                'namelist': path,
                'argno': self.argno,
                'id': self.id,
                'desc': self.desc,
                'value': self.value,
                'traceback': self.traceback}


#     def XXXstruct(self):
#         namel = []
#         cls = self.__class__
#
#         while 1:
#             if cls.__dict__.has_key('invisible'):
#                 # If the class under consideration has an "invisible"
#                 # attribute itself (rather than an inherited one),
#                 # pass to the next stage.
#                 pass
#             else:
#                 # Otherwise add it's name to the name list.
#                 if cls.__dict__.has_key('name'):
#                     # If it has a non-inherited "name" attribute, use that.
#                     namel.append(cls.name)
#                 else:
#                     # Otherwise use the class' own error_name_for_class
#                     # method (inherited). Using self.error_name_for_class()
#                     # would use the error object's such method for all
#                     # classes, but classes up the chain expect their
#                     # own to be used.
#                     namel.append(cls.error_name_for_class(self, cls))
#
#             # Now iterate over all base classes, and find one that is
#             # a subclass of RPCError. Other base classes are uninteresting.
#             # If a class inherits multiple times from RPCError, something
#             # else is very weird, and it is undefined what the "name"
#             # should be in the final error struct.
#             for cls in cls.__bases__:
#                 if issubclass(cls, RPCCError):
#                     break
#             else:
#                 raise ValueError("No RPCError base class... Eh? WHAT?!")
#
#             # ...and stop the iteration when we reach up to RPCError.
#             if cls == RPCCError:
#                 break
#
#         namel.reverse()
#
#         return {'name': '::'.join(namel),
#                 'namelist': namel,
#                 'argno': self.argno,
#                 'id': self.id,
#                 'desc': self.desc,
#                 'value': self.value,
#                 'traceback': self.traceback}


# The naming standard is that base class errors have "Error" in their
# names, while others do not. This makes the error look pretty to the
# client: LookupError::MalformedString::RegexpMismatch is prettier
# than LookupError::MalformedStringError::RegexpMismatchError.


class ExtInternalError(ExtError):
    name = "InternalError"


class ExtValueError(ExtError):
    name = "ValueError"


class ExtMalformedStringError(ExtValueError):
    pass


class ExtUnhandledCharatersError(ExtMalformedStringError):
    desc = "The string contained characters that this call can't handle."


class ExtStringTooLongError(ExtMalformedStringError):
    desc = "The string exceeds the maximum length for this type, which is %d characters."

    def __init__(self, maxlen, **kwargs):
        self.desc = self.desc % (maxlen,)
        ExtMalformedStringError.__init__(self, **kwargs)


class ExtRegexpMismatchError(ExtMalformedStringError):
    desc = "The string did not match the regexp for this type, which is '%s'."

    def __init__(self, regexp, **kwargs):
        self.desc = self.desc % (regexp,)
        ExtMalformedStringError.__init__(self, **kwargs)


class ExtStringNotInEnumError(ExtValueError):
    desc = "The string is not among the valid values: "

    def __init__(self, valid, **kwargs):
        self.desc += ", ".join(valid)
        ExtValueError.__init__(self, **kwargs)


class ExtIntegerOutOfRangeError(ExtValueError):
    desc = "Integer out of range for this type, which is %d-%d"

    def __init__(self, range, **kwargs):
        self.desc = self.desc % range
        ExtValueError.__init__(self, **kwargs)


class ExtMalformedStructError(ExtValueError):
    pass


class ExtIncompleteStructError(ExtMalformedStructError):
    desc = "Struct is incomplete, the mandatory key %s is missing"

    def __init__(self, key, **kwargs):
        self.desc = self.desc % (key,)
        ExtMalformedStructError.__init__(self, **kwargs)


class ExtUnknownStructKeyError(ExtMalformedStructError):
    desc = "The struct has a key which is not defined for this type."


class ExtLookupError(ExtError):
    name = 'LookupError'


class ExtInvalidSessionIDError(ExtLookupError):
    desc = 'No session by that id is active for this client'


class ExtFunctionNotFoundError(ExtLookupError):
    desc = 'No function by that name is callable on the server in the api version you selected'


class ExtAPIVersionNotFoundError(ExtLookupError):
    desc = 'No such API version exists on the server.'


class ExtTypeError(ExtError):
    name = 'TypeError'


class ExtExpectedStringError(ExtTypeError):
    pass


class ExtExpectedIntegerError(ExtTypeError):
    pass


class ExtExpectedBooleanError(ExtTypeError):
    pass


class ExtExpectedNullError(ExtTypeError):
    pass


class ExtExpectedStructError(ExtTypeError):
    pass


class ExtExpectedListError(ExtTypeError):
    pass


class ExtRuntimeError(ExtError):
    name = "RuntimeError"


class ExtAccessDeniedError(ExtRuntimeError):
    pass


class ExtTransportError(ExtError):
    name = "TransportError"


class ExtMalformedXMLRPCError(ExtTransportError):
    desc = 'The data you sent could not be parsed as an XMLRPC request. Perhaps the XML is malformed, or i sent in another encoding than the <?xml?>-tag claims?'


class ExtMalformedJSONError(ExtTransportError):
    desc = "The data you sent could not be parsed as a JSON request. Perhaps you sent malformed JSON, or it wasn't a struct with the 'function' and 'params' keys?"
