import asyncio
import os

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TOKEN')

from game import GameManager


bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

    for guild in bot.guilds:
        print(
            f'{bot.user} is connected to the following guild:\n'
            f'{guild.name}(id: {guild.id})'
        )

        members = '\n - '.join([member.name for member in guild.members])
        print(f'Guild Members:\n - {members}')

@bot.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        f.write(f'Exception in {event}: {args[0]}\n')

manager = GameManager()

@bot.command(name='start', help='Starts a new trivia game')
async def start_game(ctx, num_questions=10):
    guild = ctx.message.guild.name
    channel = ctx.message.channel.name

    started = manager.start_game(ctx, guild, channel, num_questions)
    if started:
        await ctx.send(f'Starting game with {num_questions} questions')

@bot.command(name='stop', help='Stops the current game')
async def stop_game(ctx):
    guild = ctx.message.guild.name
    channel = ctx.message.channel.name

    stopped = await manager.stop_game(guild, channel)
    if stopped:
        await ctx.send('Stopped game')

@bot.command(name='ignore', help='Ignore question')
async def ignore_question(ctx):
    guild = ctx.message.guild.name
    channel = ctx.message.channel.name

    question = await manager.ignore_question(guild, channel)
    if question:
        await ctx.send(f'Ignored question: {question.get_question()}, answer: {question.get_answer()}')

@bot.event
async def on_message(message):
    if bot.user == message.author:
        return
    await manager.process_message(message)
    await bot.process_commands(message)

async def game_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        for game in manager.games.values():
            await game.advance_game()
        await asyncio.sleep(1)


bot.loop.create_task(game_loop())
bot.run(TOKEN)
