from discord.ext import commands
import discord, logging


def get_emoji(letter: str) -> str:
    """Return a letter emoji representing the given capital letter"""
    letter = ord(letter)
    # 127462 is the A emoji
    return chr(127462 + (letter - 65))


def get_letter(emoji: str) -> str:
    """Return a letter representing the given letter emoji"""
    emoji = ord(emoji)
    return chr(emoji - 127397)


class Roles(commands.Cog):
    def __init__(self, bot, db, cur):
        self.bot = bot
        self.db = db
        self.cur = cur

    # Helpers
    async def send_message(self):
        """Generates or updates the roles message and puts the content in the
        configured channel"""
        msg = 'React with one of the emotes below to be given the indicated vanity role:\n'
        for role in self.cur.execute('SELECT * from roles'):
            msg += f"* {role[1]} = {get_emoji(role[0])}\n"
        chan = self.bot.get_channel(int(self.bot.getConfig('Roles',
                                                           'Channel')))
        if chan is not None:  # There is a channel set, right?
            #  Did we send the last message (Old role message)? Then edit it
            try:
                last_msg = await chan.fetch_message(
                    chan.last_message_id)  # Docs say to do it this way
            except discord.NotFound:
                last_msg = None
            if last_msg is not None and last_msg.author == self.bot.user:
                await last_msg.edit(content=msg)
            else:  # Otherwise, send a new message
                await chan.send(content=msg)

    @commands.command(usage="#somechannel")
    @commands.has_permissions(manage_roles=True)
    async def rolechan(self, ctx):
        """Sets the channel in which the bot posts the role message"""
        chan = ctx.message.channel_mentions[0]
        if chan.id == self.bot.getConfig('Roles', 'Channel'):
            return
        self.bot.setConfig('Roles', 'Channel', str(chan.id))
        await self.send_message()
        await ctx.send('Channel set!')

    @commands.command(usage='LETTER @somerole')
    @commands.has_permissions(manage_roles=True)
    async def roleset(self, ctx, letter):
        """Assigns a letter to a role"""
        code = ord(letter.upper())
        # A message can only have 20 reacts, so limit to the first 20 letters
        if code < 64 or code > 84:
            await ctx.send('That\'s not a valid letter, Try A-S')
            return
        role = ctx.message.role_mentions[0]
        if not role.hoist:
            await ctx.send(
                'That role isn\'t hoisted, not much point in assigning it...')
            return
        self.cur.execute('DELETE FROM roles WHERE letter=?', (letter, ))
        self.cur.execute('INSERT INTO roles (letter, name) VALUES (?,?)',
                         (letter, role.name))
        self.db.commit()
        await self.send_message()
        await ctx.send('Role set!')

    @commands.Cog.listener()
    async def on_reaction_add(self, react, user):
        print('React listener fired')
        chan_id = react.message.channel.id
        if chan_id == int(
                self.bot.getConfig('Roles', 'Channel')
        ) and react.message.id == react.message.channel.last_message_id:
            entry = self.cur.execute('SELECT * FROM roles where letter=?',
                                     (get_letter(str(react), ))).fetchone()
            role = discord.utils.get(react.guild.roles, name=entry[1])
            if not role:
                logging.error(
                    'User attempted to add role %s which was not found, ignoring',
                    entry[1])
                return
            await user.add_roles(role)