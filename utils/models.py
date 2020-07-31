import collections
import datetime

import discord
import typing
from tortoise import Tortoise, fields
from tortoise.models import Model

if typing.TYPE_CHECKING:
    from utils.ctx_class import MyContext


class DefaultDictJSONField(fields.JSONField):
    def __init__(self, default_factory: typing.Callable = int, **kwargs: typing.Any):
        self.default_factory = default_factory
        kwargs["default"] = collections.defaultdict(default_factory)
        super().__init__(**kwargs)

    def to_python_value(self, value: typing.Optional[typing.Union[str, dict, list]]) -> typing.Optional[collections.defaultdict]:
        ret = super().to_python_value(value)
        return collections.defaultdict(self.default_factory, ret)

    def to_db_value(self, value: typing.Optional[collections.defaultdict], instance: typing.Union[typing.Type[Model], Model]) -> typing.Optional[str]:
        value = dict(value)
        return super().to_db_value(value, instance)


class PercentageField(fields.SmallIntField):
    # TODO: Use constraints when they go out :)
    def to_db_value(self, value: typing.Any, instance: typing.Union[typing.Type[Model], Model]):
        value = min(100, max(0, int(value)))
        return super().to_db_value(value, instance)


# TODO : https://github.com/long2ice/aerich
class DiscordGuild(Model):
    id = fields.IntField(pk=True)

    discord_id = fields.BigIntField()
    name = fields.TextField()
    prefix = fields.CharField(20, null=True)
    permissions = fields.JSONField(default={})

    language = fields.CharField(6, default="en")

    class Meta:
        table = "guilds"

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Guild name={self.name}>"


class DiscordChannel(Model):
    id = fields.IntField(pk=True)

    guild = fields.ForeignKeyField('models.DiscordGuild')
    discord_id = fields.BigIntField()
    name = fields.TextField()
    permissions = fields.JSONField(default={})

    webhook_urls = fields.JSONField(default=[])

    # Generic settings
    use_webhooks = fields.BooleanField(default=True)
    use_emojis = fields.BooleanField(default=True)
    enabled = fields.BooleanField(default=False)
    giveback_at = fields.DatetimeField

    tax_on_user_send = PercentageField(default=5)
    mentions_when_killed = fields.BooleanField(default=True)
    show_duck_lives = fields.BooleanField(default=True)

    # Luck percentages
    kill_on_miss_chance = PercentageField(default=3)
    duck_frighten_chance = PercentageField(default=7)

    # Shop items
    clover_min_experience = fields.SmallIntField(default=1)
    clover_max_experience = fields.SmallIntField(default=10)

    # Experience
    base_duck_exp = fields.SmallIntField(default=10)
    per_life_exp = fields.SmallIntField(default=7)

    # Spawn rates
    ducks_per_day = fields.SmallIntField(default=96)

    spawn_weight_normal_ducks = fields.SmallIntField(default=100)
    spawn_weight_super_ducks = fields.SmallIntField(default=15)
    spawn_weight_baby_ducks = fields.SmallIntField(default=7)
    spawn_weight_prof_ducks = fields.SmallIntField(default=10)
    spawn_weight_ghost_ducks = fields.SmallIntField(default=1)
    spawn_weight_moad_ducks = fields.SmallIntField(default=5)
    spawn_weight_mechanical_ducks = fields.SmallIntField(default=1)
    spawn_weight_armored_ducks = fields.SmallIntField(default=3)
    spawn_weight_golden_ducks = fields.SmallIntField(default=1)
    spawn_weight_plastic_ducks = fields.SmallIntField(default=6)
    spawn_weight_kamikaze_ducks = fields.SmallIntField(default=6)

    # Duck settings
    ducks_time_to_live = fields.SmallIntField(default=660)  # Seconds
    super_ducks_min_life = fields.SmallIntField(default=2)
    super_ducks_max_life = fields.SmallIntField(default=7)

    class Meta:
        table = "channels"

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Channel name={self.name}>"


class DiscordUser(Model):
    id = fields.IntField(pk=True)
    discord_id = fields.BigIntField()
    name = fields.TextField()
    discriminator = fields.CharField(4)
    last_modified = fields.DatetimeField(auto_now=True)
    times_ran_example_command = fields.IntField(default=0)
    permissions = fields.JSONField(default={})

    language = fields.CharField(6, default="en")

    class Meta:
        table = "users"

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<User name={self.name}#{self.discriminator}>"


def _before_current_time_property(field):
    @property
    def is_done(self):
        return getattr(self, field) > datetime.datetime.utcnow()

    return is_done


class Player(Model):
    id = fields.IntField(pk=True)
    channel = fields.ForeignKeyField('models.DiscordChannel')
    member = fields.ForeignKeyField('models.DiscordMember')

    # Generic stats
    experience = fields.BigIntField(default=0)
    spent_experience = fields.BigIntField(default=0)
    murders = fields.SmallIntField(default=0)

    givebacks = fields.IntField(default=0)

    found_items = DefaultDictJSONField()

    # Weapon stats
    shots_without_ducks = fields.IntField(default=0)
    effective_reloads = fields.IntField(default=0)
    no_magazines_reloads = fields.IntField(default=0)
    unneeded_reloads = fields.IntField(default=0)

    bullets = fields.IntField(default=6)
    magazines = fields.IntField(default=2)

    # Weapon & Player status
    last_giveback = fields.DatetimeField(auto_now_add=True)

    weapon_confiscated = fields.BooleanField(default=False)
    weapon_jammed = fields.BooleanField(default=False)
    weapon_sabotaged_by = fields.ForeignKeyField('models.Player', null=True, on_delete=fields.SET_NULL)
    sand_in_weapon = fields.BooleanField(default=False)

    is_dazzled = fields.BooleanField(default=False)
    wet_until = fields.DatetimeField(auto_now_add=True)

    # Shop items

    clover_experience = fields.IntField(null=True)
    infrared_detector_uses_left = fields.IntField(null=True)

    clover_until = fields.DatetimeField(auto_now_add=True)
    ap_ammo_until = fields.DatetimeField(auto_now_add=True)
    explosive_ammo_until = fields.DatetimeField(auto_now_add=True)
    infrared_detector_until = fields.DatetimeField(auto_now_add=True)
    grease_until = fields.DatetimeField(auto_now_add=True)
    sight_until = fields.DatetimeField(auto_now_add=True)
    silencer_until = fields.DatetimeField(auto_now_add=True)
    sunglasses_until = fields.DatetimeField(auto_now_add=True)

    # Timers

    is_wet = _before_current_time_property("wet_until")
    have_clover = _before_current_time_property("clover_until")
    have_ap_ammo = _before_current_time_property("ap_ammo_until")
    have_explosive_ammo = _before_current_time_property("explosive_ammo_until")
    have_grease = _before_current_time_property("grease_until")
    have_sight = _before_current_time_property("sight_until")
    have_silencer = _before_current_time_property("silencer_until")
    have_sunglasses = _before_current_time_property("sunglasses_until")

    @property
    def have_infrared_detector(self):
        return self.infrared_detector_uses_left > 0 and self.infrared_detector_until > datetime.datetime.utcnow()

    # Killed ducks stats
    best_times = DefaultDictJSONField(default_factory=lambda: 660)
    killed = DefaultDictJSONField()
    hugged = DefaultDictJSONField()
    hurted = DefaultDictJSONField()
    resisted = DefaultDictJSONField()
    frightened = DefaultDictJSONField()

    async def get_bonus_experience(self, given_experience):
        return 0

    class Meta:
        table = "players"

    def __repr__(self):
        return f"<Player member={self.member} channel={self.channel}>"


class DiscordMember(Model):
    id = fields.IntField(pk=True)
    guild = fields.ForeignKeyField('models.DiscordGuild')
    user = fields.ForeignKeyField('models.DiscordUser')
    permissions = fields.JSONField(default={})

    class Meta:
        table = "members"

    def __repr__(self):
        return f"<Member user={self.user} guild={self.guild}>"


async def get_from_db(discord_object, as_user=False):
    if isinstance(discord_object, discord.Guild):
        db_obj = await DiscordGuild.filter(discord_id=discord_object.id).first()
        if not db_obj:
            db_obj = DiscordGuild(discord_id=discord_object.id, name=discord_object.name)
            await db_obj.save()
        return db_obj
    elif isinstance(discord_object, discord.TextChannel):
        db_obj = await DiscordChannel.filter(discord_id=discord_object.id).first()
        if not db_obj:
            db_obj = DiscordChannel(discord_id=discord_object.id, name=discord_object.name, guild=await get_from_db(discord_object.guild))
            await db_obj.save()
        return db_obj
    elif isinstance(discord_object, discord.Member) and not as_user:
        db_obj = await DiscordMember.filter(user__discord_id=discord_object.id).first().prefetch_related("user", "guild")
        if not db_obj:
            db_obj = DiscordMember(guild=await get_from_db(discord_object.guild), user=await get_from_db(discord_object, as_user=True))
            await db_obj.save()
        return db_obj
    elif isinstance(discord_object, discord.User) or isinstance(discord_object, discord.Member) and as_user:
        db_obj = await DiscordUser.filter(discord_id=discord_object.id).first()
        if not db_obj:
            db_obj = DiscordUser(discord_id=discord_object.id, name=discord_object.name, discriminator=discord_object.discriminator)
            await db_obj.save()
        return db_obj


async def get_player(member: discord.Member, channel: discord.TextChannel):
    db_obj = await Player.filter(member__user__discord_id=member.id, channel__discord_id=channel.id).first()
    if not db_obj:
        db_obj = Player(channel=await get_from_db(channel), member=await get_from_db(member, as_user=False))
        await db_obj.save()
    return db_obj


async def get_ctx_permissions(ctx: 'MyContext') -> dict:
    """
    Discover the permissions for a specified context. Permissions are evaluated first from the default permissions
    specified in the config file, then by the guild config, the channel conifg, and again from the member_specific
    permissions, then by the fixed permissions as seen in the config file, and finally using user overrides set by
    the bot administrator in the database.
    :param ctx:
    :return:
    """
    if ctx.guild:
        db_member: DiscordMember = await get_from_db(ctx.author)
        db_channel: DiscordChannel = await get_from_db(ctx.channel)
        db_user: DiscordUser = db_member.user
        db_guild: DiscordGuild = db_member.guild
        guild_permissions = db_guild.permissions
        channel_permissions = db_channel.permissions
        member_permissions = db_member.permissions
        user_permissions = db_user.permissions
        subguild_permissions = {}
        subchannel_permissions = {}
        for role in ctx.author.roles:
            subguild_permissions = {**subguild_permissions, **guild_permissions.get(str(role.id), {})}
            subchannel_permissions = {**subchannel_permissions, **channel_permissions.get(str(role.id), {})}
    else:
        subguild_permissions = {}
        subchannel_permissions = {}
        member_permissions = {}
        db_user: DiscordUser = await get_from_db(ctx.author, as_user=True)
        user_permissions = db_user.permissions

    default_permissions = ctx.bot.config['permissions']['default']
    fixed_permissions = ctx.bot.config['permissions']['fixed']

    permissions = {**default_permissions, **subguild_permissions, **subchannel_permissions, **member_permissions, **fixed_permissions, **user_permissions}
    return permissions


async def init_db_connection(config):
    tortoise_config = {
        'connections': {
            # Dict format for connection
            'default': {
                'engine': 'tortoise.backends.asyncpg',
                'credentials': {
                    'host': config['host'],
                    'port': config['port'],
                    'user': config['user'],
                    'password': config['password'],
                    'database': config['database'],
                }
            },
        },
        'apps': {
            'models': {
                'models': ["utils.models", "aerich.models"],
                'default_connection': 'default',
            }
        }
    }

    await Tortoise.init(tortoise_config)

    await Tortoise.generate_schemas()
