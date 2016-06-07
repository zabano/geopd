"""
Operational database interface.
"""
import hashlib
import os.path
import pkg_resources
from datetime import datetime
from urllib import quote_plus

from geopd.orm import db
from geopd.orm import Base
from geopd.util import name2key
from geopd.util import titlecase
from flask import request
from flask import current_app
from flask import url_for
from flask_login import UserMixin
from flask_login import current_user
from ipaddress import ip_address
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

from sqlalchemy.schema import Table
from sqlalchemy.schema import Column
from sqlalchemy.schema import ForeignKey
from sqlalchemy.types import Boolean
from sqlalchemy.types import DateTime
from sqlalchemy.types import Date
from sqlalchemy.types import LargeBinary
from sqlalchemy.types import Integer
from sqlalchemy.types import BigInteger
from sqlalchemy.types import Float
from sqlalchemy.types import Text
from sqlalchemy.types import String

from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import false
from sqlalchemy.ext.hybrid import hybrid_property

########################################################################################################################
# Constants
########################################################################################################################


PASSWORD_HASH_LENGTH = 128

GENDER_UNKNOWN = 0
GENDER_FEMALE = 1
GENDER_MALE = 2

USER_STATUS_PENDING = 0
USER_STATUS_ACTIVE = 1
USER_STATUS_DISABLED = 2

GRAVATAR_DEFAULT_URL = 'http://www.can.ubc.ca/avatar.png'

########################################################################################################################
# Tables
########################################################################################################################


user_survey_clinical_table = Table('user_survey_clinical', Base.metadata,
                           Column('user_id', Integer, ForeignKey('user_survey.user_id'), primary_key=True),
                           Column('clinical_id', Integer, ForeignKey('clinical_survey.id'), primary_key=True))

user_survey_epidemiologic_table = Table('user_survey_epidemiologic', Base.metadata,
                                Column('user_id', Integer, ForeignKey('user_survey.user_id'), primary_key=True),
                                Column('epidemiologic_id', Integer, ForeignKey('epidemiologic_survey.id'),
                                       primary_key=True))

user_survey_biospecimen_table = Table('user_survey_biospecimen', Base.metadata,
                              Column('user_id', Integer, ForeignKey('user_survey.user_id'), primary_key=True),
                              Column('biospecimen_id', Integer, ForeignKey('biospecimen_survey.id'), primary_key=True))

project_investigator_table = Table('project_investigator', Base.metadata,
                                   Column('project_id', Integer, ForeignKey('project.id'), primary_key=True),
                                   Column('investigator_id', Integer, ForeignKey('user.id'), primary_key=True))

core_leader_table = Table('core_leader', Base.metadata,
                          Column('core_id', Integer, ForeignKey('core.id'), primary_key=True),
                          Column('leader_id', Integer, ForeignKey('user.id'), primary_key=True))


########################################################################################################################
# Models
########################################################################################################################


class User(UserMixin, Base):
    __jsonapi_type__ = 'users'
    __jsonapi_fields__ = ['email', 'name', 'status', 'created_on', 'last_seen']

    id = Column(Integer, primary_key=True)
    email = Column(Text, unique=True, nullable=False)
    last_name = Column(Text, nullable=False)
    given_names = Column(Text, nullable=False)
    status_id = Column(Integer, ForeignKey('user_status.id'), nullable=False,
                       default=USER_STATUS_PENDING, server_default=str(USER_STATUS_PENDING))

    created_on = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen = Column(DateTime)
    confirmed = Column(Boolean, nullable=False, default=False, server_default=false())
    force_password_reset = Column(Boolean, nullable=False, default=False, server_default=false())

    _last_ip = Column('last_ip', BigInteger)
    _password = Column('password', String(PASSWORD_HASH_LENGTH), nullable=False)
    _avatar_hash = Column('avatar_hash', String(32), nullable=False)

    status = relationship('UserStatus', foreign_keys=[status_id])

    bio = relationship('UserBio', primaryjoin="User.id == UserBio.user_id", uselist=False)
    address = relationship('UserAddress', primaryjoin="User.id == UserAddress.user_id", uselist=False)
    survey = relationship('UserSurvey', primaryjoin="User.id == UserSurvey.user_id", uselist=False)
    avatar = relationship('UserAvatar', primaryjoin="User.id == UserAvatar.user_id", uselist=False)

    core_posts = relationship('CorePost', back_populates='author')

    def __init__(self, email, password, last_name, given_names):

        self.email = email
        self.password = password
        self.last_name = titlecase(last_name)
        self.given_names = titlecase(given_names)
        self._avatar_hash = hashlib.md5(email).hexdigest()

        db.flush()
        self.avatar = UserAvatar(self.id)
        self.bio = UserBio(self.id)
        self.address = UserAddress(self.id)
        self.survey = UserSurvey(self.id)

    @hybrid_property
    def name(self):
        return self.given_names + ' ' + self.last_name

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self._password = generate_password_hash(password)

    @property
    def last_ip(self):
        return str(ip_address(self._last_ip))

    @last_ip.setter
    def last_ip(self, ip_addr):
        self._last_ip = int(ip_address(unicode(ip_addr)))

    def is_active(self):
        return self.status_id == USER_STATUS_ACTIVE

    def check_password(self, password):
        """
        Check password against stored hash.

        :param str password: password (in clear text)
        :rtype: bool
        :return: True on success, otherwise False
        """
        return check_password_hash(self._password, password)

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.add(self)
        return True

    def gravatar(self, size=50, default=quote_plus(GRAVATAR_DEFAULT_URL), rating='g'):

        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        return '{url}/{hash}.png?s={size}&d={default}&r={rating}'.format(url=url, hash=self._avatar_hash,
                                                                         size=size, default=default, rating=rating)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        else:
            if data.get('confirm') != self.id:
                return False
            self.confirmed = True
            db.add(self)
            return True

    def ping(self):
        from flask import request
        self.last_ip = request.remote_addr
        self.last_seen = datetime.utcnow()

    def __repr__(self):
        return "<User({0})>".format(self.name)

    def __str__(self):
        return self.name


class UserStatus(Base):
    __jsonapi_fields__ = ['name']

    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)

    def __init__(self, status_id, name):
        self.id = status_id
        self.name = name

    def __repr__(self):
        return "<UserStatus({0})>".format(self.name)

    def __str__(self):
        return self.name


class UserAvatar(Base):
    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True, autoincrement=False)
    data = Column(LargeBinary)
    mimetype = Column(Text)

    def __init__(self, user_id):
        self.user_id = user_id


class UserAddress(Base):
    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True, autoincrement=False)
    institution = Column(Text)
    street = Column(Text)
    city = Column(Text)
    region = Column(Text)
    postal = Column(Text)
    country = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)

    def __init__(self, user_id):
        self.user_id = user_id

    def load(self, form):
        self.street = form.get('street', None)
        self.city = form.get('city', None)
        self.region = form.get('region', None)
        self.postal = form.get('postal', None)
        self.country = form.get('country', None)
        self.institution = form.get('institution', None)
        self.latitude = form.get('lat', None)
        self.longitude = form.get('lng', None)

    def __repr__(self):
        return "<UserAddress({0})>".format(self.user_id)

    def __str__(self):
        if current_user.is_authenticated:
            region = "{0} {1}".format(self.region, self.postal) if self.postal else self.region
            return ', '.join([s for s in self.street, self.city, region, self.country if s])

        return ', '.join([s for s in self.city, self.region, self.country if s])


class UserBio(Base):
    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True, autoincrement=False)
    research_interests = Column(Text)
    research_experience = Column(Text)

    def __init__(self, user_id):
        self.user_id = user_id

    def __repr__(self):
        return "<UserBio({0})>".format(self.user_id)


class UserSurvey(Base):
    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True, autoincrement=False)

    ethical = Column(Boolean)
    ethical_explain = Column(Text)
    consent = Column(Boolean)
    consent_explain = Column(Text)
    consent_sharing = Column(Boolean)
    sample = Column(Boolean)
    completed_on = Column(DateTime)

    clinical = relationship('ClinicalSurvey', secondary=user_survey_clinical_table)
    epidemiologic = relationship('EpidemiologicSurvey', secondary=user_survey_epidemiologic_table)
    biospecimen = relationship('BiospecimenSurvey', secondary=user_survey_biospecimen_table)

    def __init__(self, user_id):
        self.user_id = user_id

    def __repr__(self):
        return "<UserSurvey({0})>".format(self.user_id)


class ClinicalSurvey(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<ClinicalSurvey({0})>'.format(self.name)

    def __str__(self):
        return self.name


class EpidemiologicSurvey(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<EpidemiologicSurvey({0})>'.format(self.name)

    def __str__(self):
        return self.name


class BiospecimenSurvey(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<BiospecimenSurvey({0})>'.format(self.name)

    def __str__(self):
        return self.name


class Project(Base):
    __jsonapi_type__ = 'projects'
    __jsonapi_fields__ = ['name', 'description']

    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text, unique=True, nullable=False)

    investigators = relationship('User', secondary=project_investigator_table)

    def __init__(self, name, description, investigators=[]):
        self.name = name
        self.description = description
        self.investigators = investigators

    def __repr__(self):
        return "<Project(key='{0}')>".format(self.name)

    def __str__(self):
        return self.name


class Publication(Base):
    __jsonapi_type__ = 'publications'
    __jsonapi_fields__ = ['title', 'source', 'issue', 'volume', 'pages', 'authors', 'published_on', 'epublished_on']

    id = Column(Integer, primary_key=True, autoincrement=False)  # PubMed
    title = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    issue = Column(Text, nullable=False)
    volume = Column(Text, nullable=False)
    pages = Column(Text, nullable=False)
    authors = Column(Text, nullable=False)
    abstract = Column(Text)
    published_on = Column(Date, nullable=False)
    epublished_on = Column(Date)

    def __init__(self, id, title):
        self.id = id
        self.title = title

    @property
    def pdf_url(self):
        filename = os.path.join('pubmed', '{0}.pdf'.format(self.id))
        fullpath = pkg_resources.resource_filename('geopd', os.path.join('static', filename))
        if os.path.exists(fullpath):
            return url_for('static', filename='pubmed/{0}.pdf'.format(self.id))

    def __repr__(self):
        return "<Publication({0})>".format(self.id)

    def __str__(self):
        return self.title


class Meeting(Base):
    __jsonapi_type__ = 'meetings'
    __jsonapi_fields__ = ['city', 'year']

    id = Column(Integer, primary_key=True)
    city = Column(Text(convert_unicode=True), nullable=False)
    year = Column(Integer, nullable=False, unique=True)
    carousel = Column(Boolean, nullable=False, default=False, server_default=false())
    program = Column(Boolean, nullable=False, default=False, server_default=false())

    def __init__(self, city, year, carousel=None, program=None):
        self.city = city
        self.year = year
        self.carousel = carousel
        self.program = program

    @property
    def title(self):
        return "{0} {1}".format(self.city, self.year)

    @property
    def key(self):
        return name2key(self.title)

    @property
    def image_url(self):
        return url_for('static', filename='images/meetings/{0}.jpg'.format(self.city.lower()))

    def __repr__(self):
        return "<Meeting({0})>".format(self.title)

    def __str__(self):
        return self.title


class Core(Base):
    __jsonapi_type__ = 'cores'
    __jsonapi_fields__ = ['name', 'key']

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    key = Column(Text, nullable=False, unique=True)

    leaders = relationship('User', secondary=core_leader_table)
    posts = relationship('CorePost', back_populates='core')

    def __init__(self, name, key):
        self.name = name
        self.key = key

    @property
    def image_url(self):
        return url_for('static', filename='images/cores/{0}.jpg'.format(self.key))

    def __repr__(self):
        return "<Core({0})>".format(self.name)

    def __str__(self):
        return self.name


class CorePost(Base):
    __jsonapi_type__ = 'core-posts'
    __jsonapi_fields__ = ['body', 'created_on']

    id = Column(Integer, primary_key=True)
    body = Column(Text, nullable=False)
    created_on = Column(Text, nullable=False, default=datetime.utcnow)
    author_id = Column(Integer, ForeignKey('user.id'))
    core_id = Column(Integer, ForeignKey('core.id'))

    author = relationship('User', foreign_keys=[author_id], back_populates='core_posts')
    core = relationship('Core', foreign_keys=[core_id], back_populates='posts')

    def __init__(self, body, author=current_user):
        self.body = body
        self.author = author

    def __repr__(self):
        return "<Core({0})>".format(self.id)

    def __str__(self):
        return "Core Post #{0}".format(self.id)
