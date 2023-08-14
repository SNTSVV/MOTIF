##################################################################
# print an error message and exit program with a return code
# :param _string: error message
# :param _return_code: return code
# :return:
##################################################################
def error_exit(_string, _return_code=1):
    print(_string)
    exit(_return_code)


