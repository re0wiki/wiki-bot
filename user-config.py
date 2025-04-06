# This is an automatically generated file. You can find more
# configuration parameters in 'config.py' file or refer
# https://doc.wikimedia.org/pywikibot/master/api_ref/pywikibot.config.html

# The family of sites to be working on.
# Pywikibot will import families/xxx_family.py so if you want to change
# this variable, you have to ensure that such a file exists. You may use
# generate_family_file to create one.
family = "re0"

# The site code (language) of the site to be working on.
mylang = "zh"

# The dictionary usernames should contain a username for each site where you
# have a bot account. If you have a unique username for all sites of a
# family , you can use '*'
usernames["re0"]["zh"] = "IchiSanNi"

# The list of BotPasswords is saved in another file. Import it if needed.
# See https://www.mediawiki.org/wiki/Manual:Pywikibot/BotPasswords to know how
# use them.
password_file = "user-password.py"

# ############# EXTERNAL EDITOR SETTINGS ##############
# The command for the editor you want to use. If set to True, Tkinter
# editor will be used. If set to False, no editor will be used. In
# script tests to be a noop (like /bin/true) so the script continues.
# If set to None, the EDITOR environment variable will be used as
# command. If EDITOR is not set, on Windows platforms it tries to
# determine the default text editor from registry. Finally, Tkinter is
# used as fallback.
editor: bool | str | None = None

# Warning: DO NOT use an editor which doesn't support Unicode to edit pages!
# You will BREAK non-ASCII symbols!
editor_encoding = "utf-8"

# The temporary file name extension can be set in order to use syntax
# highlighting in your text editor.
editor_filename_extension = "wiki"

# ############# LOGFILE SETTINGS ##############

# Defines for which scripts a logfile should be enabled. Logfiles will be
# saved in the 'logs' subdirectory.
#
# Example:
#     log = ['redirect', 'replace', 'weblinkchecker']
# It is also possible to enable logging for all scripts, using this line:
#     log = ['*']
# To disable all logging, use this:
#     log = []
# Per default, no logging is enabled.
# This setting can be overridden by the -log or -nolog command-line arguments.
log: list[str] = ["*"]
# filename defaults to modulename-bot.log
logfilename: str | None = None
# maximal size of a logfile in kilobytes. If the size reached that limit the
# logfile will be renamed (if logfilecount is not 0) and the old file is filled
# again. logfilesize must be an integer value
logfilesize = 1024
# Number of rotating logfiles are created. The older files get the higher
# number. If logfilecount is 0, no logfile will be archived but the current
# logfile will be overwritten if the file size reached the logfilesize above.
logfilecount = 5
# set to 1 (or higher) to generate "informative" messages to terminal
verbose_output = 0
# set to True to fetch the pywiki version online
log_pywiki_repo_version = False
# if True, include a lot of debugging info in logfile
# (overrides log setting above)
debug_log: list[str] = []

# ############# EXTERNAL SCRIPT PATH SETTINGS ##############
# Set your own script path to lookup for your script files.
#
# Your private script path is relative to your base directory.
# Subfolders must be delimited by '.'. every folder must contain
# an (empty) __init__.py file.
#
# The search order is
# 1. user_script_paths in the given order
# 2. scripts/userscripts
# 3. scripts
# 4. scripts/maintenance
# 5. pywikibot/scripts
#
# 2. - 4. are available in directory mode only
#
# sample:
# user_script_paths = ['scripts.myscripts']
user_script_paths: list[str] = ["scripts"]

# ############# EXTERNAL FAMILIES SETTINGS ##############
# Set your own family path to lookup for your family files.
#
# Your private family path may be either an absolute or a relative path.
# You may have multiple paths defined in user_families_paths list.
#
# You may also define various family files stored directly in
# family_files dict. Use the family name as dict key and the path or an
# url as value.
#
# samples:
# family_files['mywiki'] = 'https://de.wikipedia.org'
# user_families_paths = ['data/families']
user_families_paths: list[str] = []

# ############# IMAGE RELATED SETTINGS ##############
# If you set this to True, images will be uploaded to Wikimedia
# Commons by default.
upload_to_commons = False

# ############# SETTINGS TO AVOID SERVER OVERLOAD ##############

# Slow down the robot such that it never requests a second page within
# 'minthrottle' seconds. This can be lengthened if the server is slow,
# but never more than 'maxthrottle' seconds. However - if you are running
# more than one bot in parallel the times are lengthened.
#
# 'maxlag' is used to control the rate of server access (see below).
# Set minthrottle to non-zero to use a throttle on read access.
minthrottle = 0
maxthrottle = 60

# Slow down the robot such that it never makes a second page edit within
# 'put_throttle' seconds.
put_throttle: int | float = 0

# Sometimes you want to know when a delay is inserted. If a delay is larger
# than 'noisysleep' seconds, it is logged on the screen.
noisysleep = 0

# Defer bot edits during periods of database server lag. For details, see
# https://www.mediawiki.org/wiki/Manual:Maxlag_parameter
# You can set this variable to a number of seconds, or to None (or 0) to
# disable this behavior. Higher values are more aggressive in seeking
# access to the wiki.
# Non-Wikimedia wikis may or may not support this feature; for families
# that do not use it, it is recommended to set minthrottle (above) to
# at least 1 second.
maxlag = 5

# Maximum of pages which can be retrieved at one time from wiki server.
# -1 indicates limit by api restriction
step = -1

# Maximum number of times to retry an API request before quitting.
max_retries = 15
# Minimum time to wait before resubmitting a failed API request.
retry_wait = 5
# Maximum time to wait before resubmitting a failed API request.
retry_max = 120

# ############# DATABASE SETTINGS ##############
# Setting to connect the database or replica of the database of the wiki.
# db_name_format can be used to manipulate the dbName of site.
#
# Example for a pywikibot running on Wikimedia Cloud (Toolforge):
# db_hostname_format = '{0}.analytics.db.svc.wikimedia.cloud'
# db_name_format = '{0}_p'
# db_connect_file = user_home_path('replica.my.cnf')
db_hostname_format = "localhost"
db_username = ""
db_password = ""
db_name_format = "{0}"
db_connect_file = user_home_path(".my.cnf")
# local port for mysql server
# ssh -L 4711:enwiki.analytics.db.svc.eqiad.wmflabs:3306 \
#     user@login.toolforge.org
db_port = 3306

# ############# HTTP SETTINGS ##############
# Default socket timeout in seconds.
# DO NOT set to None to disable timeouts. Otherwise this may freeze your
# script.
# You may assign either a tuple of two int or float values for connection and
# read timeout, or a single value for both.
# See also: https://requests.readthedocs.io/en/stable/user/advanced/#timeouts
socket_timeout = (6.05, 45)


# ############# COSMETIC CHANGES SETTINGS ##############
# The bot can make some additional changes to each page it edits, e.g. fix
# whitespace or positioning of category links.

# This is an experimental feature; handle with care and consider re-checking
# each bot edit if enabling this!
cosmetic_changes = False

# If cosmetic changes are switched on, and you also have several accounts at
# projects where you're not familiar with the local conventions, you probably
# only want the bot to do cosmetic changes on your "home" wiki which you
# specified in config.mylang and config.family.
# If you want the bot to also do cosmetic changes when editing a page on a
# foreign wiki, set cosmetic_changes_mylang_only to False, but be careful!
cosmetic_changes_mylang_only = True

# The dictionary cosmetic_changes_enable should contain a tuple of languages
# for each site where you wish to enable in addition to your own langlanguage
# (if cosmetic_changes_mylang_only is set)
# Please set your dictionary by adding such lines to your user config file:
# cosmetic_changes_enable['wikipedia'] = ('de', 'en', 'fr')
cosmetic_changes_enable: dict[str, tuple[str, ...]] = {}

# The dictionary cosmetic_changes_disable should contain a tuple of languages
# for each site where you wish to disable cosmetic changes. You may use it with
# cosmetic_changes_mylang_only is False, but you can also disable your own
# language. This also overrides the settings in the cosmetic_changes_enable
# dictionary. Please set your dict by adding such lines to your user config:
# cosmetic_changes_disable['wikipedia'] = ('de', 'en', 'fr')
cosmetic_changes_disable: dict[str, tuple[str, ...]] = {}

# cosmetic_changes_deny_script is a list of scripts for which cosmetic changes
# are disabled. You may add additional scripts by appending script names in
# your user config file ("+=" operator is strictly recommended):
# cosmetic_changes_deny_script += ['your_script_name_1', 'your_script_name_2']
# Appending the script name also works:
# cosmetic_changes_deny_script.append('your_script_name')
cosmetic_changes_deny_script = [
    "category_redirect",
    "cosmetic_changes",
    "newitem",
    "touch",
    "revertbot",
]

# ############# FURTHER SETTINGS ##############

# Simulate settings

# Defines what additional actions the bots are NOT allowed to do (e.g. 'edit')
# on the wiki server. Allows simulation runs of bots to be carried out without
# changing any page on the server side. Use this setting to add more actions
# into user config file for wikis with extra write actions.
actions_to_block: list[str] = []

# Set simulate to True or use -simulate option to block all actions given
# above.
simulate: bool | str = False

# How many pages should be put to a queue in asynchronous mode.
# If maxsize is <= 0, the queue size is infinite.
# Increasing this value will increase memory space but could speed up
# processing. As higher this value this effect will decrease.
max_queue_size = 64

# Pickle protocol version to use for storing dumps.
# This config variable is not used for loading dumps.
# Version 0 is a more or less human-readable protocol
# Version 2 is common to both Python 2 and 3, and should
# be used when dumps are accessed by both versions.
# Version 3 is only available for Python 3
# Version 4 is only available for Python 3.4+
# Version 5 was added with Python 3.8
pickle_protocol = 2

# ############# INTERWIKI SETTINGS ##############

# Should interwiki.py report warnings for missing links between foreign
# languages?
interwiki_backlink = False

# Should interwiki.py display every new link it discovers?
interwiki_shownew = False

# Should interwiki.py output a graph PNG file on conflicts?
# You need pydot for this:
# https://pypi.org/project/pydot/
interwiki_graph = False

# Specifies that the robot should process that amount of subjects at a time,
# only starting to load new pages in the original language when the total
# falls below that number. Default is to process (at least) 100 subjects at
# once.
interwiki_min_subjects = 100

# If interwiki graphs are enabled, which format(s) should be used?
# Supported formats include png, jpg, ps, and svg. See:
# https://graphviz.org/docs/outputs/
# If you want to also dump the dot files, you can use this in your
# user config file:
# interwiki_graph_formats = ['dot', 'png']
# If you need a PNG image with an HTML image map, use this:
# interwiki_graph_formats = ['png', 'cmap']
# If you only need SVG images, use:
# interwiki_graph_formats = ['svg']
interwiki_graph_formats = ["png"]

# You can post the contents of your autonomous_problems.dat to the wiki,
# e.g. to https://de.wikipedia.org/wiki/Wikipedia:Interwiki-Konflikte .
# This allows others to assist you in resolving interwiki problems.
# To help these people, you can upload the interwiki graphs to your
# webspace somewhere. Set the base URL here, e.g.:
# 'https://www.example.org/~yourname/interwiki-graphs/'
interwiki_graph_url = None

# Save file with local articles without interwikis.
without_interwiki = False

# ############# SOLVE_DISAMBIGUATION SETTINGS ############
#
# Set disambiguation_comment[FAMILY][LANG] to a non-empty string to override
# the default edit comment for the solve_disambiguation bot.
#
# Use %s to represent the name of the disambiguation page being treated.
# Example:
#
# disambiguation_comment['wikipedia']['en'] = \
#    'Robot-assisted disambiguation ([[WP:DPL|you can help!]]): %s'

# Sorting order for alternatives. Set to True to ignore case for sorting order.
sort_ignore_case = False

# ############# WEBLINK CHECKER SETTINGS ##############

# How many external links should weblinkchecker.py check at the same time?
# If you have a fast connection, you might want to increase this number so
# that slow servers won't slow you down.
max_external_links = 50

report_dead_links_on_talk = False

# Don't alert on links days_dead old or younger
weblink_dead_days = 7

# ############# REPLICATION BOT SETTINGS ################
# You can add replicate_replace to your user config file.
#
# Use has the following format:
#
# replicate_replace = {
#            'wikipedia:li': {'Hoofdpagina': 'Veurblaad'}
# }
#
# to replace all occurrences of 'Hoofdpagina' with 'Veurblaad' when writing to
# liwiki. Note that this does not take the origin wiki into account.
replicate_replace: dict[str, dict[str, str]] = {}
