import atexit
from apscheduler.schedulers.background import BackgroundScheduler

from src.service.followers.FollowerUpdater import FollowerUpdater
from src.util.meta.Singleton import Singleton


class Scheduler(metaclass=Singleton):

    def __init__(self):
        self.scheduler = BackgroundScheduler()

    def set_up(self):
        # self.scheduler.add_job(func=FollowerUpdater.update_followers, trigger='interval', seconds=10)
        # Execute at 00:00:00 every day
        self.scheduler.add_job(func=FollowerUpdater.update_followers, trigger='cron', hour=0, minute=0, second=0)
        self.scheduler.start()
        atexit.register(lambda: self.scheduler.shutdown())
