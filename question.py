from math import floor
from random import randint
import pickle
import json
import urllib
from threading import Lock
import re

import Levenshtein
import requests
from bs4 import BeautifulSoup
from num2words import num2words

STOP_WORDS = ['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"]


CATEGORIES_URL = 'https://trivia.fyi/categories/'


OPENT_SESSION_TOKEN_URL = 'https://opentdb.com/api_token.php?command=request'
OPENT_CATEGORY_URL = 'https://opentdb.com/api_category.php'
OPENT_URL = 'https://opentdb.com/api.php?amount=50&encode=url3986&type=multiple&token='

DISCORD_UNDERSCORE = '\_'
MAXMIMUM_DISTANCE = 2


TEST_QUESTIONS = (
    ('How many eyes does Kevin Fugate have?', 'One'),
    ('What food did Tyler eat that was so big?', 'Hot dog'),
    ('What was the name of the stripper Tom met in ATL?', 'Picante'),
    ('What did Tan test when he worked in a lab?', 'Piss'),
    ('What character did Alec make a big play with in LoL?', 'Amumu'),
    ('What girl couldn\'t Jrn get it up for? (aka Dva Bomb)', 'Gabby'),
    ('What prevented Tom from seeing the sky when he moved to Seattle?', 'Smoke'),
    ('What is Kacper better known as on Skype?', 'Engineer Phillip'),
    ('What drug was Andy Carlson addicted to?', 'Xanax'),
    ('To whom did Andy once say: \"My life is so much better than yours\"?', 'Tyler'),
    ('What did Tan once call Kacper in a fit of rage?', 'Insufferable Twat'),
    ('What is Alec\'s favorite strain of kush?', 'White Widow'),
    ('Under what piece of furniture could you find Tom\'s headset in high school?', 'Bed'),
    ('What was Tom\'s best stock pick of all time?', 'SPHS')
)

# wrapper that will generate hints
class Question:

    def __init__(self, question, answer, detail=None):
        self.question = question
        self.answer = answer
        self.ignore = False
        self.details = None

    def __eq__(self, other):
        # substrings to speed up comparison
        return other.get_question()[0:25] == self.get_question()[0:25] and other.get_answer()[0:25] == self.get_answer()[0:25]

    def get_details(self):
        return self.details

    def is_ignored(self):
        return self.ignore

    def ignore_question(self):
        self.ignore = True

    def get_question(self):
        return self.question

    def get_answer(self):
        return self.answer

    def is_answer_correct(self, guess):
        if len(self.answer) == 1 or self.answer.isnumeric():
            return guess.lower() == self.answer

        if guess.isnumeric():
            if guess.lower() == self.answer:
                return True
            guess = num2words(guess)

        question = self.question.lower()
        question = re.sub(r'[^A-Za-z0-9 ]+', '', question)
        answer = self.answer.lower()
        answer = re.sub(r'[^A-Za-z0-9 ]+', '', answer)
        guess = guess.lower()
        guess = re.sub(r'[^A-Za-z0-9 ]+', '', guess)

        question_tokens = question.split(' ')
        answer_tokens = answer.split(' ')
        guess_tokens = guess.split(' ')

        answer_tokens = list(filter(lambda x: x not in STOP_WORDS and x not in question_tokens, answer_tokens))
        guess_tokens = list(filter(lambda x: x not in STOP_WORDS and x not in question_tokens, guess_tokens))

        correct_tokens = 0
        for guess_token in guess_tokens:
            for answer_token in answer_tokens:
                max_distance = MAXMIMUM_DISTANCE
                if len(answer_token) > 6:
                    max_distance = 1
                elif len(answer_token) < 5:
                    max_distance = 0

                if Levenshtein.distance(answer_token, guess_token) <= max_distance:
                    correct_tokens += 1
                    # significant word should be worth more
                    if len(answer_token) > 8:
                        correct_tokens += 1

        if len(answer_tokens) == 1:
            return correct_tokens >= 1

        return correct_tokens > floor(len(answer_tokens) / 2)

    def _get_hint(self, percentage):
        answer_length = len(re.sub(r'[^A-Za-z0-9]+', '', self.answer))
        num_visible_letter = floor(answer_length * percentage)
        if num_visible_letter == 0:
            num_visible_letter = 1

        valid_indexes = []
        for i in range(answer_length):
            # if self.answer[i] != ' ':
            if self.answer[i].isalnum():
                valid_indexes.append(i)

        letter_indexes = []
        for i in range(num_visible_letter):
            index = randint(0, len(valid_indexes) - 1)
            letter_indexes.append(valid_indexes[index])
            valid_indexes.pop(index)

        hint = ''
        for i in range(len(self.answer)):
            if i in letter_indexes:
                hint += self.answer[i]
            elif self.answer[i] == ' ':
                # two spaces for better formatting
                hint += '  '
            elif not self.answer[i].isalnum():
                # keep punctuation
                hint += self.answer[i]
            else:
                hint += DISCORD_UNDERSCORE


        return hint

    def get_first_hint(self):
        return self._get_hint(1/5)

    def get_second_hint(self):
        return self._get_hint(3/5)


# extra details in parenthesis
def parse_answer(answer):
    parsed = answer
    parsed.replace('\n', ' ')

    bracket_index = -1
    if '(' in answer:
        bracket_index = answer.index('(')

    details = None
    if bracket_index >= 0:
        details = parsed[bracket_index:]
        parsed = parsed[0:bracket_index]


    if parsed != answer:
        print(f'{parsed} - {answer}')

    parsed = parsed.strip()
    return (parsed, details)

class QuestionDatabase:

    def __init__(self, scrape=True):
        self.lock = Lock()
        if scrape:
            self.questions = self._scrape_questions()
        else:
            self.questions = self.read_question_database()

    def get_questions(self):
        return self.questions

    def _scrape_trivia_fyi(self):
        categories = []

        response = requests.get(CATEGORIES_URL)
        bs = BeautifulSoup(response.content, "html.parser")
        category_tds = bs.find_all('td')
        for td in category_tds:
            link = td.find('a')
            categories.append({'category': link.text, 'link': link.attrs['href']})

        questions = {}
        for category in categories:
            found = True
            link = category['link']
            page = 1
            questions[category['category']] = []
            while found:
                response = requests.get(link, allow_redirects=False)
                bs = BeautifulSoup(response.content, "html.parser")
                qs = bs.find_all('article')

                if not qs:
                    found = False
                for q in qs:
                    question = q.find('a').text
                    answer, details = parse_answer(q.find('div', {'class': 'su-spoiler-content'}).text)
                    questions[category['category']].append(Question(question, answer, details))
                page += 1
                link = category['link'] + "/page/" + str(page)

        return [q for c in questions.values() for q in c]

    def _scrape_opentdb(self):
        token = json.loads(requests.get(OPENT_SESSION_TOKEN_URL).content)['token']

        all_questions = []
        while True:
            response = json.loads(requests.get(OPENT_URL + token).content)
            if response['response_code'] != 0:
                break
            for q in response['results']:
                question = urllib.parse.unquote(q['question']).strip()
                if 'anime' in question.lower():
                    continue
                answer = urllib.parse.unquote(q['correct_answer']).strip()
                all_questions.append(Question(question, answer))
        return all_questions


    def _scrape_questions(self):
        all_questions = self._scrape_trivia_fyi() + self._scrape_opentdb()
        old_questions = self.read_question_database()

        old_question_map = {}
        for question in old_questions:
            old_question_map[question.get_question() + question.get_answer()] = question

        for question in old_questions:
            if question.get_question() + question.get_answer() not in old_question_map:
                all_questions.append(question)
            elif question.is_ignored():
                all_questions[all_questions.index(question)].ignore_question()

        self._update_question_database(all_questions)
        return all_questions

    def _update_question_database(self, all_questions):
        self.lock.acquire()
        self._write(all_questions)
        self.lock.release()

    def read_question_database(self):
        self.lock.acquire()
        questions = []
        try:
            questions = self._read()
        except Exception as e:
            pass
        self.lock.release()
        return questions

    def ignore_question(self, question):
        self.lock.acquire()
        all_questions = self._read()
        index = all_questions.index(question)
        if index >= 0:
            all_questions[index].ignore_question()
        self._write(all_questions)
        self.lock.release()

    def _write(self, all_questions):
        f = open('questions.pkl', 'wb')
        pickle.dump(all_questions, f)
        f.close()

    def _read(self):
        f = open('questions.pkl', 'rb')
        questions = pickle.load(f)
        f.close()
        return questions


Question_Database = QuestionDatabase(scrape=True)

