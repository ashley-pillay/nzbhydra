from enum import Enum
import json
import logging
import os
import collections
import random
import string

from typing import List

logger = logging.getLogger('root')


class Category(object):
    def __init__(self, parent, name, title=None):
        if not title:
            title = name
        self.parent = parent
        self.title = title
        self.categoryname = name
        self.children = []
        self.parent.add_category(self)

    @property
    def path(self):
        return "%s%s." % (self.parent.path, self.categoryname)  # Parent path already includes a dot (or not in case of the category root) 

    def get(self):
        return self.parent.get_category(self)

    def add_category(self, category):
        self.parent.get_category(self)[category.categoryname] = {}
        self.children.append(category)

    def add_setting(self, setting):
        self.parent.get_category(self)[setting.settingname] = setting.default
        if setting not in self.children:
            self.children.append(setting)

    def get_category(self, category):
        return self.get()[category.categoryname]

    def get_setting(self, setting):
        return self.get()[setting.settingname]

    def set_setting(self, setting, value):
        self.get()[setting.settingname] = value

    def __setattr__(self, key, value):
        if key != "children" and hasattr(self, "children") and key in [x.settingname for x in self.children if isinstance(x, Setting)] and not isinstance(value, Setting):
            # Allow setting a setting's value directly instead of using set(value)
            self.get()[key] = value
        else:
            return super().__setattr__(key, value)

    def __getattribute__(self, *args, **kwargs):
        key = args[0]
        # todo maybe, only works with direct subsettings
        # if key != "children" and hasattr(self, "children") and key in [x.settingname for x in self.children if isinstance(x, Setting)]:
        #    return self.get()[key]

        return super().__getattribute__(*args, **kwargs)


cfg = {}
config_file = None


class CategoryRoot(Category):
    def __init__(self):
        self.children = []
        pass

    @property
    def path(self):
        return ""

    def add_category(self, category):
        cfg[category.categoryname] = {}
        self.children.append(category)

    def add_setting(self, setting):
        cfg[setting.settingname] = setting
        self.children.append(setting)

    def get(self):
        return cfg

    def get_category(self, category):
        return cfg[category.categoryname]


config_root = CategoryRoot()


class SettingType(Enum):
    free = "free"
    password = "password"
    select = "select"
    multiselect = "multiselect"


class Setting(object):
    """
    A setting that has a category, name, a default value, a value type and a comment. These will be delegated to profig to read and set the actual config.
    This structure allows us indexed access to the settings anywhere in the code without having to use dictionaries with potentially wrong string keys.
    It also allows us to collect all settings and create a dict with all settings which can be serialized and sent to the GUI.
    """

    def __init__(self, parent: Category, name: str, default: object, valuetype: type, title=None, description: str = None, setting_type: SettingType = SettingType.free):
        self.parent = parent
        self.settingname = name
        self.default = default
        self.valuetype = valuetype
        self.description = description
        self.setting_type = setting_type
        self.title = title
        self.parent.add_setting(self)

    @property
    def path(self):
        return "%s%s" % (self.parent.path, self.settingname)  # Parent path already includes a trailing dot

    def get(self):
        # We delegate the getting of the actual value to the parent
        return self.parent.get_setting(self)

    def get_with_default(self, default):
        return self.get() if not None else default

    def set(self, value):
        self.parent.set_setting(self, value)
        
    def isSetting(self, value):
        return self.get() == value or self.get() == getattr(value, "name")

    def __str__(self):
        return "%s: %s" % (self.settingname, self.get())

    def __eq__(self, other):
        if not isinstance(other, Setting):
            return False
        return self.parent == other.parent and self.settingname == other.settingname


class SelectOption(object):
    def __init__(self, name, title):
        super().__init__()
        self.name = name
        self.title = title

    def __eq__(self, other):
        if isinstance(other, SelectOption):
            return self.name == other.name
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class SelectionSetting(Setting):
    def __init__(self, parent: Category, name: str, default: SelectOption, valuetype: type, options: List[SelectOption], title: str = None, description: str = None, setting_type: SettingType = SettingType.select):  # Warning is a mistake by PyCharm
        super().__init__(parent, name, default, valuetype, title, description, setting_type)
        self.options = options
        self.parent.get()[self.settingname] = self.default.name

    def get(self):
        return super().get()


class MultiSelectionSetting(Setting):
    def __init__(self, parent: Category, name: str, default: List[SelectOption], valuetype: type, options: List[SelectOption], title: str = None, description: str = None, setting_type: SettingType = SettingType.select):  # Warning is a mistake by PyCharm
        super().__init__(parent, name, default, valuetype, title, description, setting_type)
        self.options = options
        self.parent.get()[self.settingname] = [x.name for x in self.default]

    def get(self):
        return super().get()
    

class OrderedMultiSelectionSetting(Setting):
    def __init__(self, parent: Category, name: str, default: List[SelectOption], valuetype: type, options: List[SelectOption], title: str = None, description: str = None, setting_type: SettingType = SettingType.select):  # Warning is a mistake by PyCharm
        super().__init__(parent, name, default, valuetype, title, description, setting_type)
        self.options = options
        self.parent.get()[self.settingname] = [x.name for x in self.default]

    def get(self):
        return super().get()


def update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def load(filename):
    global cfg
    global config_file
    config_file = filename
    if os.path.exists(filename):
        with open(filename, "r") as f:
            loaded_config = json.load(f)
            cfg = update(cfg, loaded_config)
            pass


def import_config_data(data):
    global cfg
    global config_file
    cfg = data
    save(config_file)


def save(filename):
    global cfg
    with open(filename, "w") as f:
        json.dump(cfg, f, indent=4)


def get(setting: Setting) -> object:
    """
    Just a legacy way to access the setting 
    """
    return setting.get()


def set(setting: Setting, value: object):
    """
    Just a legacy way to set the setting 
    """
    setting.set(value)



class LoglevelSelection(object):
    critical = SelectOption("CRITICAL", "Critical")
    error = SelectOption("ERROR", "Error")
    warning = SelectOption("WARNING", "Warning")
    info = SelectOption("INFO", "Info")
    debug = SelectOption("DEBUG", "Debug")

    options = [critical, error, warning, info, debug]


class LoggingSettings(Category):
    def __init__(self, parent):
        super().__init__(parent, "logging", "Logging")
        self.logfilename = Setting(self, name="logfile-filename", default="nzbhydra.log", valuetype=str)
        self.logfilelevel = SelectionSetting(self, name="logfile-level", default=LoglevelSelection.info, valuetype=str, options=LoglevelSelection.options)
        self.consolelevel = SelectionSetting(self, name="consolelevel", default=LoglevelSelection.info, valuetype=str, options=LoglevelSelection.options)


class CacheTypeSelection(object):
    file = SelectOption("file", "Cache on the file system")
    memory = SelectOption("memory", "Cache in the memory during runtime")


class MainSettings(Category):
    """
    The main settings of our program.
    """

    def __init__(self):
        super().__init__(config_root, "main", "Main")
        self.host = Setting(self, name="host", default="0.0.0.0", valuetype=str)
        self.port = Setting(self, name="port", default=5050, valuetype=int)
        self.startup_browser = Setting(self, name="startupBrowser", default=True, valuetype=bool)

        self.username = Setting(self, name="username", default="", valuetype=str)
        self.password = Setting(self, name="password", default="", valuetype=str)
        self.apikey = Setting(self, name="apikey", default=''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(30)), valuetype=str)
        self.enable_auth = Setting(self, name="enableAuth", default=False, valuetype=bool)

        self.ssl = Setting(self, name="ssl", default=False, valuetype=bool)
        self.sslcert = Setting(self, name="sslcert", default="nzbhydra.crt", valuetype=str)
        self.sslkey = Setting(self, name="sslkey", default="nzbhydra.key", valuetype=str)

        self.debug = Setting(self, name="debug", default=False, valuetype=bool)
        self.cache_enabled = Setting(self, name="enableCache", default=True, valuetype=bool)
        self.cache_type = SelectionSetting(self, name="cacheType", default=CacheTypeSelection.memory, valuetype=str, options=[CacheTypeSelection.memory, CacheTypeSelection.file])
        self.cache_timeout = Setting(self, name="cacheTimeout", default=30, valuetype=int)
        self.cache_threshold = Setting(self, name="cachethreshold", default=25, valuetype=int)
        self.cache_folder = Setting(self, name="cacheFolder", default="cache", valuetype=str)

        self.logging = LoggingSettings(self)


mainSettings = MainSettings()


class HtmlParserSelection(object):
    html = SelectOption("html.parser", "Default BS (slow)")
    lxml = SelectOption("lxml", "LXML (faster, needs to be installed separately)")

    options = [html, lxml]


class InternalExternalSelection(object):
    internal = SelectOption("internal", "Internal searches")
    external = SelectOption("external", "API searches")
    options = [internal, external]


class CategorySizeSettings(Category):
    def __init__(self, parent):
        super().__init__(parent, "categorysizes", "Category sizes")
        self.enable_category_sizes = Setting(self, name="enable_category_sizes", default=True, valuetype=bool)

        self.movieMin = Setting(self, name="moviesmin", default=500, valuetype=int)
        self.movieMax = Setting(self, name="moviesmax", default=20000, valuetype=int)

        self.moviehdMin = Setting(self, name="movieshdmin", default=2000, valuetype=int)
        self.moviehdMax = Setting(self, name="movieshdmax", default=20000, valuetype=int)

        self.moviesdMin = Setting(self, name="moviessdmin", default=500, valuetype=int)
        self.moviesdMax = Setting(self, name="movieshdmin", default=3000, valuetype=int)

        self.tvMin = Setting(self, name="tvmin", default=50, valuetype=int)
        self.tvMax = Setting(self, name="tvmax", default=5000, valuetype=int)

        self.tvhdMin = Setting(self, name="tvhdmin", default=300, valuetype=int)
        self.tvhdMax = Setting(self, name="tvhdmax", default=3000, valuetype=int)

        self.tvsdMin = Setting(self, name="tvsdmin", default=50, valuetype=int)
        self.tvsdMax = Setting(self, name="tvsdmax", default=1000, valuetype=int)

        self.audioMin = Setting(self, name="audiomin", default=1, valuetype=int)
        self.audioMax = Setting(self, name="audiomax", default=2000, valuetype=int)

        self.audioflacmin = Setting(self, name="flacmin", default=10, valuetype=int)
        self.audioflacmax = Setting(self, name="flacmax", default=2000, valuetype=int)

        self.audiomp3min = Setting(self, name="mp3min", default=1, valuetype=int)
        self.audiomp3max = Setting(self, name="mp3max", default=500, valuetype=int)

        self.consolemin = Setting(self, name="consolemin", default=100, valuetype=int)
        self.consolemax = Setting(self, name="consolemax", default=40000, valuetype=int)

        self.pcmin = Setting(self, name="pcmin", default=100, valuetype=int)
        self.pcmax = Setting(self, name="pcmax", default=50000, valuetype=int)

        self.xxxmin = Setting(self, name="xxxmin", default=100, valuetype=int)
        self.xxxmax = Setting(self, name="xxxmax", default=10000, valuetype=int)


class SearchingSettings(Category):
    """
    How searching is executed.
    """

    def __init__(self):
        super().__init__(config_root, "searching", "Searching")
        self.timeout = Setting(self, name="timeout", default=5, valuetype=int)
        self.ignore_disabled = Setting(self, name="ignoreTemporarilyDisabled", default=False, valuetype=bool)
        self.generate_queries = MultiSelectionSetting(self, name="generate_queries", default=[InternalExternalSelection.internal], options=InternalExternalSelection.options, valuetype=str, setting_type=SettingType.multiselect)
        
        self.duplicateSizeThresholdInPercent = Setting(self, name="duplicateSizeThresholdInPercent", default=0.1, valuetype=float)
        self.duplicateAgeThreshold = Setting(self, name="duplicateAgeThreshold", default=3600, valuetype=int)
        self.htmlParser = SelectionSetting(self, name="htmlParser", default=HtmlParserSelection.html, valuetype=str, options=HtmlParserSelection.options)


        self.category_sizes = CategorySizeSettings(self)


searchingSettings = SearchingSettings()


class NzbAccessTypeSelection(object):
    serve = SelectOption("serve", "Proxy the NZBs from the indexer")
    redirect = SelectOption("redirect", "Redirect to the indexer")
    direct = SelectOption("direct", "Use direct links to the indexer")


class NzbAddingTypeSelection(object):
    link = SelectOption("link", "Send link to NZB")
    nzb = SelectOption("nzb", "Upload NZB")


class DownloaderSelection(object):
    sabnzbd = SelectOption("sabnzbd", "SabNZBd")
    nzbget = SelectOption("nzbget", "NZBGet")


class DownloaderSettings(Category):
    def __init__(self):
        super().__init__(config_root, "downloader", "Downloader")
        self.nzbaccesstype = SelectionSetting(self, name="nzbaccesstype", default=NzbAccessTypeSelection.serve, valuetype=str, options=[NzbAccessTypeSelection.direct, NzbAccessTypeSelection.redirect, NzbAccessTypeSelection.serve])
        self.nzbAddingType = SelectionSetting(self, name="nzbAddingType", default=NzbAddingTypeSelection.nzb, valuetype=str, options=[NzbAddingTypeSelection.link, NzbAddingTypeSelection.nzb])
        self.downloader = SelectionSetting(self, name="downloader", default=DownloaderSelection.nzbget, valuetype=str, options=[DownloaderSelection.nzbget, DownloaderSelection.sabnzbd])


downloaderSettings = DownloaderSettings()


class SabnzbdSettings(Category):
    def __init__(self):
        super().__init__(downloaderSettings, "sabnzbd", "SabNZBD")
        self.host = Setting(self, name="host", default="127.0.0.1", valuetype=str)
        self.port = Setting(self, name="port", default=8086, valuetype=int)
        self.ssl = Setting(self, name="ssl", default=False, valuetype=bool)
        self.apikey = Setting(self, name="apikey", default=None, valuetype=str)
        self.username = Setting(self, name="username", default=None, valuetype=str)
        self.password = Setting(self, name="password", default=None, valuetype=str)


sabnzbdSettings = SabnzbdSettings()


class NzbgetSettings(Category):
    def __init__(self):
        super().__init__(downloaderSettings, "nzbget", "NZBGet")
        self.host = Setting(self, name="host", default="127.0.0.1", valuetype=str)
        self.port = Setting(self, name="port", default=6789, valuetype=int)
        self.ssl = Setting(self, name="ssl", default=False, valuetype=bool)
        self.username = Setting(self, name="username", default="nzbget", valuetype=str)
        self.password = Setting(self, name="password", default="tegbzn6789", valuetype=str)


nzbgetSettings = NzbgetSettings()


class SearchIdSelection(object):
    rid = SelectOption("rid", "TvRage ID")
    tvdbid = SelectOption("tvdbid", "TVDB ID")
    imdbid = SelectOption("imdbid", "IMDB ID")


class IndexerSettingsAbstract(Category):
    def __init__(self, parent, name, title):
        super().__init__(parent, name, title)
        self.name = Setting(self, name="name", default=None, valuetype=str)
        self.host = Setting(self, name="host", default=None, valuetype=str)
        self.enabled = Setting(self, name="enabled", default=True, valuetype=bool)
        self.search_ids = MultiSelectionSetting(self, name="search_ids", default=[], valuetype=list,
                                                options=[SearchIdSelection.imdbid, SearchIdSelection.rid, SearchIdSelection.tvdbid],
                                                setting_type=SettingType.multiselect)
        self.score = Setting(self, name="score", default=0, valuetype=str)


class IndexerBinsearchSettings(IndexerSettingsAbstract):
    def __init__(self, parent):
        super(IndexerBinsearchSettings, self).__init__(parent, "binsearch", "Binsearch")
        self.host = Setting(self, name="host", default="https://binsearch.com", valuetype=str)
        self.name = Setting(self, name="name", default="binsearch", valuetype=str)


class IndexerNewznabSettings(IndexerSettingsAbstract):
    def __init__(self, parent, name, title):
        super(IndexerNewznabSettings, self).__init__(parent, name, title)
        self.apikey = Setting(self, name="apikey", default=None, valuetype=str)
        self.search_ids = MultiSelectionSetting(self, name="search_ids", default=[SearchIdSelection.imdbid, SearchIdSelection.rid, SearchIdSelection.tvdbid], valuetype=list,
                                                options=[SearchIdSelection.imdbid, SearchIdSelection.rid, SearchIdSelection.tvdbid],
                                                setting_type=SettingType.multiselect)
        self.enabled = Setting(self, name="enabled", default=False, valuetype=bool)  # Disable by default because we have no meaningful initial data


class IndexerNzbclubSettings(IndexerSettingsAbstract):
    def __init__(self, parent):
        super(IndexerNzbclubSettings, self).__init__(parent, "nzbclub", "NZBClub")
        self.host = Setting(self, name="host", default="http://nzbclub.com", valuetype=str)
        self.name = Setting(self, name="name", default="nzbclub", valuetype=str)


class IndexerNzbindexSettings(IndexerSettingsAbstract):
    def __init__(self, parent):
        super(IndexerNzbindexSettings, self).__init__(parent, "nzbindex", "NZBIndex")
        self.host = Setting(self, name="host", default="https://nzbindex.com", valuetype=str)
        self.name = Setting(self, name="name", default="nzbindex", valuetype=str)
        self.general_min_size = Setting(self, name="generalMinSize", default=1, valuetype=int)


class IndexerWombleSettings(IndexerSettingsAbstract):
    def __init__(self, parent):
        super(IndexerWombleSettings, self).__init__(parent, "womble", "Womble")
        self.host = Setting(self, name="host", default="https://newshost.co.za", valuetype=str)
        self.name = Setting(self, name="name", default="womble", valuetype=str)


class IndexerSettings(Category):
    def __init__(self):
        super().__init__(config_root, "indexers", "Indexer")
        self.binsearch = IndexerBinsearchSettings(self)
        self.nzbclub = IndexerNzbclubSettings(self)
        self.nzbindex = IndexerNzbindexSettings(self)
        self.womble = IndexerWombleSettings(self)
        self.newznab1 = IndexerNewznabSettings(self, "newznab1", "Newznab 1")
        self.newznab2 = IndexerNewznabSettings(self, "newznab2", "Newznab 2")
        self.newznab3 = IndexerNewznabSettings(self, "newznab3", "Newznab 3")
        self.newznab4 = IndexerNewznabSettings(self, "newznab4", "Newznab 4")
        self.newznab5 = IndexerNewznabSettings(self, "newznab5", "Newznab 5")
        self.newznab6 = IndexerNewznabSettings(self, "newznab6", "Newznab 6")


indexerSettings = IndexerSettings()


class IndexerNewznab1Settings(IndexerNewznabSettings):
    def __init__(self):
        self._path = "indexers.newznab1"
        super().__init__("Newznab 1", "", "")


def get_newznab_setting_by_id(id):
    id = str(id)
    return {
        "1": indexerSettings.newznab1,
        "2": indexerSettings.newznab2,
        "3": indexerSettings.newznab3,
        "4": indexerSettings.newznab4,
        "5": indexerSettings.newznab5,
        "6": indexerSettings.newznab6}[id]
