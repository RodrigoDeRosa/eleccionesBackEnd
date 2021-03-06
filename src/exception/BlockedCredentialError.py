class BlockedCredentialError(Exception):

    def __init__(self, credential=None):
        self.message = f'Credential blocked.'
        self.credential = credential

    def __str__(self):
        return self.message
