import threading
from datetime import datetime
from random import randint

from question import Question, Question_Database


class GameManager:

    def __init__(self):
        self.games = {}

    def _get_key(self, guild, channel):
        return f'{guild}:{channel}'

    def start_game(self, ctx, guild, channel, num_questions):
        key = self._get_key(guild, channel)
        if key in self.games:
            return self.games[key].start(ctx, num_questions)

        self.games[key] = TriviaGame(ctx, num_questions)
        return True

    def stop_game(self, guild, channel):
        key = self._get_key(guild, channel)
        if key in self.games:
            return self.games[key].stop()
        return False

    def ignore_question(self, guild, channel):
        key = self._get_key(guild, channel)
        if key in self.games:
            return self.games[key].ignore()

    async def process_message(self, message):
        guild = message.guild.name
        channel = message.channel.name
        key = self._get_key(guild, channel)
        if key not in self.games:
            return

        await self.games[key].process_answer(message)


class QuestionsManager:

    def __init__(self, questions):
        self.questions = questions
        self.asked = []
        if not self.questions:
            raise RuntimeError('No questions found')

    def next(self):
        if not self.questions:
            self.questions = self.asked.copy()
            self.asked = []

        index = randint(0, len(self.questions) - 1)
        question = self.questions[index]

        self.questions.pop(index)
        self.asked.append(question)
        return question

class GameState:
    BEFORE_QUESTION = 1
    AWAIT_ANSWER = 2
    AWAIT_ANSWER_HINT_ONE = 3
    AWAIT_ANSWER_HINT_TWO = 4
    OVER = 5

DELAY_GAME_START_SECONDS = 4
NO_HINT_DELAY = 6
ONE_HINT_DELAY = 6
TWO_HINT_DELAY = 6

class TriviaGame:

    def __init__(self, ctx, num_questions):
        self.lock = threading.Lock()
        self.games_played = 0
        self.questions_manager = QuestionsManager(Question_Database.get_questions())
        self._reset(ctx, num_questions)

    def _reset(self, ctx, num_questions):
        self.ctx = ctx
        self.num_questions = num_questions
        self.question_counter = 0
        self.last_state = datetime.now()
        self.state = GameState.BEFORE_QUESTION
        self.games_played += 1
        self.question = None
        self.question_answered = False
        self.score_board = {}

    def start(self, ctx, num_questions):
        if self.state == GameState.OVER:
            self._reset(ctx, num_questions)
            return True
        return False

    def stop(self):
        self.lock.acquire()
        stopped = False
        if self.state != GameState.OVER:
            self.state = GameState.OVER
            stopped = True
        self.lock.release()
        return stopped

    def ignore(self):
        if self.question is None:
            return None

        self.lock.acquire()
        self.question.ignore_question()
        Question_Database.ignore_question(self.question)
        self.lock.release()
        return self.question


    def _update_scoreboard(self, author_id, author_name):
        points = 0
        if self.state == GameState.AWAIT_ANSWER:
            points = 10
        elif self.state == GameState.AWAIT_ANSWER_HINT_ONE:
            points = 5
        elif self.state == GameState.AWAIT_ANSWER_HINT_TWO:
            points = 3

        if author_id not in self.score_board:
            self.score_board[author_id] = {'name': author_name, 'score': points}
        else:
            self.score_board[author_id]['score'] += points

    def _print_scoreboard(self):
        sorted_scores = []
        for score in self.score_board.values():
            if not sorted_scores:
                sorted_scores.append(score)
            else:
                inserted = False
                for i in range(len(sorted_scores)):
                    if sorted_scores[i]['score'] >= score['score']:
                        continue
                    else:
                        sorted_scores.insert(i, score)
                        inserted = True
                        break

                if not inserted:
                    sorted_scores.append(score)

        scoreboard = ''
        for score in sorted_scores:
            scoreboard += f'{score["name"]} - {score["score"]} pts\n'
        return scoreboard



    async def process_answer(self, message):
        if self.state == GameState.BEFORE_QUESTION or self.state == GameState.OVER:
            return
        self.lock.acquire()
        author_id = message.author.id
        author_name = message.author.name
        content = message.content

        if self.question.is_answer_correct(content):
            self.question_answered = True
            self._update_scoreboard(author_id, author_name)
            await self.ctx.send(f'Correct answer {author_name}! Answer: {self.question.get_answer()}')

        self.lock.release()

    async def advance_game(self):
        if self.state == GameState.OVER:
            return

        if self.question_counter >= self.num_questions and self.state == GameState.BEFORE_QUESTION:
            self.state = GameState.OVER
            await self.ctx.send(f'Game over\n\nGame {self.games_played} ScoreBoard:\n\n{self._print_scoreboard()}\n')
            return

        if self.question_answered or (self.question and self.question.is_ignored()):
            self.state = GameState.BEFORE_QUESTION
            self.last_state = datetime.now()
            self.question_counter += 1
            self.question_answered = False
            self.question = None


        if self.state == GameState.BEFORE_QUESTION:
            if (datetime.now() - self.last_state).total_seconds() > DELAY_GAME_START_SECONDS:
                self.lock.acquire()
                self.question = self.questions_manager.next()
                await self.ctx.send(f"Question {self.question_counter + 1}:\n{self.question.get_question()}")
                self.state = GameState.AWAIT_ANSWER
                self.last_state = datetime.now()
                self.lock.release()
        elif self.state == GameState.AWAIT_ANSWER:
            if (datetime.now() - self.last_state).total_seconds() > NO_HINT_DELAY:
                self.lock.acquire()
                if not self.question_answered:
                    await self.ctx.send(f"Hint 1:\n{self.question.get_first_hint()}")
                    self.state = GameState.AWAIT_ANSWER_HINT_ONE
                    self.last_state = datetime.now()
                self.lock.release()
        elif self.state == GameState.AWAIT_ANSWER_HINT_ONE:
            if (datetime.now() - self.last_state).total_seconds() > ONE_HINT_DELAY:
                self.lock.acquire()
                if not self.question_answered:
                    await self.ctx.send(f"Hint 2:\n{self.question.get_second_hint()}")
                    self.state = GameState.AWAIT_ANSWER_HINT_TWO
                    self.last_state = datetime.now()
                self.lock.release()
        elif self.state == GameState.AWAIT_ANSWER_HINT_TWO:
            if (datetime.now() - self.last_state).total_seconds() > TWO_HINT_DELAY:
                self.lock.acquire()
                if not self.question_answered:
                    self.state = GameState.BEFORE_QUESTION
                    self.last_state = datetime.now()
                    await self.ctx.send(f"Answer:\n{self.question.get_answer()} {'' if self.question.get_details() is None else self.question.get_details()}")
                    self.question_counter += 1
                self.lock.release()
