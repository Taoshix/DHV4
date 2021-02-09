import aiohttp
from aiohttp import web
from discord.ext import commands

from utils.cog_class import Cog
import datetime
from typing import Tuple, Dict, Any, List

import discord

from utils import config, checks
from cogs.inventory_commands import INV_COMMON_ITEMS
from utils.ctx_class import MyContext
from utils.models import DiscordUser, get_from_db

config = config.load_config()["bot_lists"]


class BotsListVoting(Cog):
    """
    Handle votes for the bot on many different bot lists.
    """
    async def get_bot_dict(self) -> Dict[str, Dict[str, Any]]:
        BOTS_DICT = {
            "top_gg": {
                "name": "top.gg",
                "bot_url": "https://top.gg/bot/187636089073172481",
                "can_vote": True,
                "vote_url": "https://top.gg/bot/187636089073172481/vote",
                "vote_every": datetime.timedelta(hours=12),
                "check_vote_url": "https://top.gg/api/bots/187636089073172481/check?userId={user.id}",
                "check_vote_key": "voted",
                "auth": config["topgg_shared_secret"],
                "webhook_handler": self.votes_topgg_hook,
                "webhook_key": "topgg",
            },
            "discord_bots_gg": {
                "name": "discord.bots.gg",
                "bot_url": "https://discord.bots.gg/bots/187636089073172481",
                "can_vote": False,
            },
            "discordbotslist": {
                "name": "Discord Bots List",
                "bot_url": "",
                "can_vote": True,
                "vote_url": "",
                "vote_every": datetime.timedelta(hours=12),
                "check_vote_url": None,
                "auth": config["discordbotlist_api_token"],
                "webhook_handler": self.votes_discordbotslist_hook,
                "webhook_key": "discordbotlist",
            },
            "fateslist": {
                "name": "fateslist",
                "bot_url": "https://fateslist.xyz/bot/187636089073172481",
                "can_vote": True,
                "vote_url": "https://fateslist.xyz/bot/187636089073172481/vote",
                "vote_every": datetime.timedelta(hours=8),
                "check_vote_url": "https://fateslist.xyz/api/bots/187636089073172481/votes?user_id={user.id}",
                "check_vote_key": "voted",
                "auth": config["fateslist_api_token"],
                "webhook_handler": self.votes_fateslist_hook,
            },
        }

        return BOTS_DICT

    async def get_bot_list(self) -> List[Dict[str, Any]]:
        BOTS_LIST = list((await self.get_bot_dict()).values())

        return BOTS_LIST

    async def get_routes(self, route_prefix):
        routes = []

        for bot_list in await self.get_bot_list():
            handler = bot_list.get("webhook_handler", None)
            if handler:
                webhook_key = bot_list.get("webhook_key", bot_list["name"])
                routes.append(('POST', f'{route_prefix}/{webhook_key}/hook', handler))

        return routes

    async def votes_discordbotslist_hook(self, request: web.Request):
        """
        Handle users votes for discordbotslist
        """
        bot_list = (await self.get_bot_dict())["discordbotslist"]
        auth = request.headers.get("Authorization", "")

        if auth != bot_list["auth"]:
            self.bot.logger.warning(f"Bad authentification provided to {bot_list['name']} API.")
            return web.Response(status=401, text="Unauthorized, bad auth")

        post_data = await request.json()
        user_id = int(post_data["id"])

        result, message = await self.handle_vote(user_id, bot_list)

        if result:
            return web.Response(status=200, text=message)
        else:
            return web.Response(status=400, text=message)

    async def votes_fateslist_hook(self, request: web.Request):
        """
        Handle users votes for fateslist
        """
        bot_list = (await self.get_bot_dict())["fateslist"]
        auth = request.headers.get("Authorization", "")

        if auth != bot_list["auth"]:
            self.bot.logger.warning(f"Bad authentification provided to {bot_list['name']} API.")
            return web.Response(status=401, text="Unauthorized, bad auth")

        post_data = await request.json()
        user_id = int(post_data["id"])

        result, message = await self.handle_vote(user_id, bot_list)

        if result:
            return web.Response(status=200, text=message)
        else:
            return web.Response(status=400, text=message)

    async def votes_topgg_hook(self, request: web.Request):
        """
        Handle users votes for top.gg
        """
        bot_list = (await self.get_bot_dict())["top_gg"]
        auth = request.headers.get("Authorization", "")

        if auth != bot_list["auth"]:
            self.bot.logger.warning(f"Bad authentification provided to {bot_list['name']} API.")
            return web.Response(status=401, text="Unauthorized, bad auth")

        post_data = await request.json()
        user_id = int(post_data["user"])

        bot_id = int(post_data["bot"])

        if bot_id != self.bot.user.id:
            self.bot.logger.warning(f"Bad bot ID ({bot_id}) provided to {bot_list['name']} API.")
            return web.Response(status=401, text="Unauthorized, bad bot ID")

        is_test = post_data["type"] == "test"
        is_weekend = post_data["isWeekend"]

        multiplicator = int(is_weekend) + 1

        result, message = await self.handle_vote(user_id, bot_list, multiplicator=multiplicator, is_test=is_test)

        if result:
            return web.Response(status=200, text=message)
        else:
            return web.Response(status=400, text=message)

    async def handle_vote(self, user_id, bot_list, multiplicator=1, is_test=False) -> Tuple[bool, str]:
        try:
            user = await self.bot.fetch_user(user_id)
        except discord.errors.NotFound:
            self.bot.logger.warning(f"Bad user ID provided to votes API {bot_list['name']}: {user_id}.")
            return False, "Unauthorized, bad user ID"

        db_user: DiscordUser = await get_from_db(user)

        db_user.votes += multiplicator
        db_user.add_to_inventory(INV_COMMON_ITEMS["i_voted"])

        if not is_test:
            self.bot.logger.info(f"{multiplicator} vote(s) recorded for {user.name}#{user.discriminator} on {bot_list['name']}.")
            await db_user.save()
        else:
            self.bot.logger.warning(f"{multiplicator} test vote(s) received for {user.name}#{user.discriminator}. Not saved.")

        try:
            await user.send("✨ Thanks for voting for DuckHunt ! Check your inventory with `dh!inv` in a game channel.")
        except discord.errors.Forbidden:
            pass

        return True, "Vote recorded"

    async def can_vote(self, bot_list, user):
        vote_check_url = bot_list.get("check_vote_url", None)

        if not bot_list["can_vote"]:
            return False
        elif not vote_check_url:
            return None
        else:
            timeout = aiohttp.ClientTimeout(total=5)
            headers = {'accept': 'application/json', "Authorization": bot_list.get("auth", "")}
            self.bot.logger.debug(f"Checking user {user.id} vote on {bot_list['name']}")
            async with self.bot.client_session.get(vote_check_url.format(user=user), timeout=timeout, headers=headers) as resp:
                json_resp = await resp.json()

            self.bot.logger.debug(f"Checking user {user.id} vote on {bot_list['name']} -> {json_resp}")

            voted_resp = str(json_resp.get(bot_list['check_vote_key']))
            if voted_resp.isdigit():
                voted = bool(int(voted_resp))
            elif voted_resp.lower() == "true":
                voted = True
            elif voted_resp.lower() == "false":
                voted = False
            else:
                self.bot.logger.warning(f"Unknown response for {bot_list['name']} votechecking: {voted_resp}")
                voted = False

            return not voted

    async def get_votable_lists(self, user: discord.User):
        votable_lists = []
        maybe_lists = []
        nope_lists = []

        for bot_list in await self.get_bot_list():
            res = await self.can_vote(bot_list, user)
            if res is True:
                votable_lists.append(bot_list)
            elif res is None:
                maybe_lists.append(bot_list)
            else:
                nope_lists.append(bot_list)

        return votable_lists, maybe_lists, nope_lists



    @commands.command()
    @checks.channel_enabled()
    async def vote(self, ctx: MyContext):
        """
        Sends the link you can use to vote for DuckHunt on bot lists
        """
        _ = await ctx.get_translate_function()

        m = await ctx.reply(_("Please wait while I check where you can vote..."))

        async with ctx.typing():
            votable_lists, maybe_lists, nope_lists = await self.get_votable_lists(ctx.author)

            embed = discord.Embed()

            if votable_lists:
                text = votable_lists[0]['vote_url']
                embed.title = _("You can vote !")
                embed.description = _("Thanks for supporting the bot by voting !")
                embed.url = votable_lists[0]['vote_url']
                embed.colour = discord.Colour.green()
            elif maybe_lists:
                text = maybe_lists[0]['vote_url']
                embed.title = _("You might be able to vote !")
                embed.description = _("Thanks for supporting the bot by voting as much as you can. It makes a difference !")
                embed.url = maybe_lists[0]['vote_url']
                embed.colour = discord.Colour.orange()
            else:
                text = _("Oh no! No bot list is currently available for you to vote.")
                embed.title = _("There is nowhere for you to vote at the time !")
                embed.description = _("Thanks for supporting the bot. It makes a difference! \n"
                                      "Unfortunately, you voted everywhere you could for now, but you can check back in a few hours.")
                embed.colour = discord.Colour.red()

            for bot_list in votable_lists:
                embed.add_field(name=_("You can vote on {bl_name}", bl_name=bot_list['name']),
                                value=f"[Click me to vote]({bot_list['vote_url']}")

            for bot_list in maybe_lists:
                embed.add_field(name=_("You might be able to vote on {bl_name}", bl_name=bot_list['name']),
                                value=f"[Click me to vote]({bot_list['vote_url']}")

            await m.edit(embed=embed, content=text)


setup = BotsListVoting.setup
