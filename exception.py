
class BitbucketException(BaseException):
    def __init__(self, code, message, new_branch_name):
        self.code = code
        self.message = message
        self.new_branch_name = new_branch_name


class NoramlMessageException(BaseException):
    def __init__(self,  message):
        self.message = message


class TagNotFoundException(NoramlMessageException):
    def __init__(self):
        NoramlMessageException.__init__(self, 'Tag is not found at today')


class BranchIsExistException(NoramlMessageException):
    def __init__(self,  branch_name):
        NoramlMessageException.__init__(self, '{} is exists'.format(branch_name))
