#! py -3

import discord
import asyncio
import sqlite3, random, re
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("pocket.db")
c = conn.cursor()
client = discord.Client()

ignore_list = []

@client.event
async def on_ready():
    logging.info("Logged in as " + client.user.name + " (" + client.user.id + ")")
    ignore_list.append(client.user.id)              # Ignore self, or else Pocket would respond to himself

@client.event
async def on_message(message: discord.Message):
    logging.info(message.author.name + " (" + message.author.id + ") said \"" + message.content + "\" in " + message.channel.name)

    # Ignore those to be ignored
    if not message.author.id in ignore_list:
        addressed, content = process_meta(message)
        response = respond(message, content.strip(), addressed)
        if response:                                # Only send_message if there is a response; most of the time, there won't be.
            await client.send_message(message.channel, populate(message, response))


def process_meta(message: discord.Message) -> (bool, str):
    """
    Determines if Pocket was directly addressed, ie "Pocket, inspire me" or "pocket: give me a suggestion"
    If he was addressed, returns true and the rest of the message. If not, then return false and the message.
    Cleans up the message, too.
    """
    prefix = message.content.split()[0].lower()
    if prefix == "pocket," or prefix == "pocket:":
        return (True, message.content[7:])          # Remove the prefix ("pocket," or "Pocket:"), which is 5 chars long
    if message.content.startswith("_") and message.content.endswith("_"):
        return (False, message.contetn[1:-1])
    return (False, message.content)

def respond(context: discord.Message, message: str, addressed: bool) -> str or None:
    """
    Parses the actual message, scanning for triggers and errata.
    Returns a reply - or None, if it is not to be.
    """
    response = ""

    # If Pocket was addressed, then it might be a command
    if addressed:
        # Check for commands
        response = process_commands(message)
        if response: return response

    # If here, then it's not a command. Check for triggers.
    response = process_triggers(message)
    if response: return response

    # If addressed but still don't have a response, say so.
    if addressed: return "<unknown>"
    else: return None

def process_commands(message: str) -> str or None:
    if "<reply>" in message:
        try:
            tidbit = [portion.strip() for portion in message.split("<reply>")]
            tidbit[0] = tidbit[0].lower()       # Lowercase the trigger; it has to be case insensitive.
            c.execute("INSERT OR FAIL INTO comments (triggers, remark, protected) VALUES (?, ?, 0);", tidbit)
            conn.commit()
        except sqlite3.IntegrityError as e:
            # If IntegrityError, Pocket already has this tidbit.
            return "I already had it that way, $who."
        return "Ok, $who. \"" + tidbit[0] + "\" triggers \"" + tidbit[1] + "\"."

def process_triggers(message: str) -> str or None:
    c.execute("SELECT remark FROM comments WHERE triggers=?", (message.lower(),))
    result = c.fetchall()
    if result:
        return random.choice(result)[0]
    else: return None

def populate(context: discord.Message, response: str) -> str:
    """
    Replaces variables in a response with values. ie $who with a random active user, or $item with a random item
    Replaces <command> with an appropriate variation
    """
    # Check for phrase shortcuts
    command_response = re.compile("^<\w+>$").match(response)
    if command_response:
        c.execute("SELECT response FROM auto_responses WHERE command=?", (command_response.group(),))
        result = c.fetchall()
        if result:
            response = random.choice(result)[0]
        else: raise ValueError(response + " is not a known command.")

    ### Placeholder Operations ###

    # -- $who : replaces with the sender of the message
    response = response.replace("$who", context.author.name)

    # -- $someone : replaces with a random online user
    online_peeps = list(context.server.members)
    response = response.replace("$someone", random.choice(online_peeps).name)

    return response


client.run("a_muse_ing@mail.com", "Amusement4Masses")
