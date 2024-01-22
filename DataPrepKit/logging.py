import json
import sys
import traceback

#---------------------------------------------------------------------------------------------------

def error(exception_object):
    """Use this function to produce error messages.

    It is possible for "exception_object" to be a lambda that takes no
    arguments and returns a Exception object so that the object can be
    constructed semi-lazily. This allows the construction of the
    Exception object to be avoided entirely in the event that the
    application is not in verbose mode, i.e. there are no info logging
    functions currently set. """
    if len(__error_log_functions) > 0:
        if callable(exception_object):
            exception_object = exception_object()
        else:
            pass
        for log_func in __error_log_functions.values():
            log_func(exception_object)
    else:
        pass

def info(message_string):
    """Use this function to produce informational messages.

    It is possible for "message_string" to be a lambda that takes no
    arguments and returns a string object so that the string can be
    constructed semi-lazily. This allows the construction of the
    string to be avoided entirely in the event that the application is
    not in verbose mode, i.e. there are no info logging functions
    currently set. """
    if len(__info_log_functions) > 0:
        if callable(message_string):
            message_string = message_string()
        else:
            pass
        for log_func in __info_log_functions.values():
            log_func(message_string)
    else:
        pass

def info_json(jsonlike_object):
    """This function is similar to "info()" but expects an object that
    can be converted to a string using "json.dumps()".

    It is possible for "jsonlike_object" to be a lambda that takes no
    arguments and returns a JSON-like object that can be passed to
    "json.dumps()" so that the object can be constructed
    semi-lazily. This allows the construction of the JSON-like object
    to be avoided entirely in the event that the application is not in
    verbose mode, i.e. there are no info logging functions currently
    set. """
    if len(___info_log_functions) > 0:
        if callable(jsonlike_object):
            jsonlike_object = jsonlike_object()
        else:
            pass
        json_message = json.dumps(jsonlike_object, indent=2)
        for log_func in __info_log_functions.values():
            log_func(f'{json_message}\n')
    else:
        pass

#---------------------------------------------------------------------------------------------------

__info_log_functions = {}
__error_log_functions = {}

def reset_default_info_logger(verbose=False):
    """Use this to reset the logging facility to using the default message logger."""
    if verbose:
        __info_log_functions = {'__default__': _default_info_logger}
    else:
        __info_log_functions = {}

def reset_default_error_logger():
    """Use this to reset the logging facility to using the default error logger."""
    __error_log_functions = {'__default__': _default_error_logger}

def _default_info_logger(message_string):
    sys.stdout.write(message_string)

def _default_error_logger(exception_object):
    traceback.print_exception(exception_object)

def set_info_logger(string_id, logger):
    __info_log_functions[string_id] = logger

def set_error_logger(string_id, logger):
    __error_log_functions[string_id] = logger

def delete_info_logger(string_id):
    if string_id in __info_log_functions:
        del __info_log_functions[string_id]
    else:
        pass

def delete_error_logger(string_id):
    if string_id in __error_log_functions:
        del __error_log_functions[string_id]
    else:
        pass

#---------------------------------------------------------------------------------------------------

reset_default_info_logger()
reset_default_error_logger()
