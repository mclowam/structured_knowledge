from app.db.session import SessionDep


class KnowledgeRepository:
    def __init__(self, session: SessionDep):
        self._session = session