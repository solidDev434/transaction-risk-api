class UserRespository:
    def __init__(self, session):
        self.session = session

    async def get_user_by_id(self, user_id):
        await self.session.get(user_id)


repo = UserRespository()
