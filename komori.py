import logging
import os
import sqlite3
import time

import praw


logging.basicConfig(
    filename='komori.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'
)

class RedditClient(object):
    """
    Easily scrape Reddit posts by keyword filter, and comment
    said post with what ever content you like.
    """

    MESSAGE = 'Disposable cameras are so underrated these days!\n\n' \
        'Check out this art [project](https://www.instagram.com/thedisposablemanproject/) '\
        'I did for Burning Man 2018 where I gifted new playa friends I met a ' \
        'disposable camera, and had them return to me when all the exposures were gone.'

    BLACKLIST_SUBREDDITS = [
        'woooosh',
        'pics',
        'suicidewatch',
        'depression'
    ]

    def __init__(self, username, password, query_string, subreddit=None):
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')

        if None in [client_id, client_secret]:
            raise ValueError('Must set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET env vars.')

        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.query_string = query_string
        self.subreddit = subreddit

        self.submission_id_list = list()

        # db things
        self.conn = sqlite3.connect('reddit.db')
        self.cursor = self.conn.cursor()

    def __reddit_init(self):

        reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            username=self.username,
            password=self.password,
            user_agent='web:thedisposablemanproject:v0.0.1 (by /u/komoribot)'
        )

        return reddit

    def __is_blacklisted(self, subreddit):
        return True if subreddit in self.BLACKLIST_SUBREDDITS else False

    def __fetch_all_submission_ids(self):
        self.cursor.execute("SELECT * FROM submissions")
        self.submission_id_list = [id_[0] for id_ in self.cursor.fetchall()]


    def __insert_submission_id(self, sub_id):
        with self.conn:
            self.cursor.execute("INSERT INTO submissions (submissionid) Values ('%s')" % sub_id)

    def __create_db(self):
        with self.conn:
            self.cursor.execute("CREATE TABLE IF NOT EXISTS submissions (submissionid text)")

    def run(self):

        if not self.subreddit:
            self.subreddit = 'all'

        self.__fetch_all_submission_ids()

        reddit = self.__reddit_init()

        submissions = reddit.subreddit(self.subreddit).search(self.query_string)

        count = 0

        # submissions will be a generator
        for submission in submissions:
            if self.__is_blacklisted(submission.subreddit.display_name): continue

            if not submission.archived and submission.id not in self.submission_id_list:
                try:
                    submission.reply(self.MESSAGE)
                except praw.exceptions.APIException as e:
                    logging.warning('Rate limit exceeded. Sleeping program for 10 minutes')
                    time.sleep(600)
                    continue

                count += 1
                self.__insert_submission_id(submission.id)
                msg = 'Left comment on %s in "/r/%s" with id %s' % \
                    (submission.title, submission.subreddit.display_name, submission.id)
                logging.info(msg)

        logging.info('Commented on %s total threads.', str(count))

        self.conn.close()


if __name__ == '__main__':
    client = RedditClient('komoribot', os.getenv('KOMORI_BOT_PASSWORD'), 'disposable camera')
    client.run()
