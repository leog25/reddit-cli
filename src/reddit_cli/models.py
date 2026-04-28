from pydantic import BaseModel, ConfigDict, Field


class Post(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    author: str
    subreddit: str
    score: int
    upvote_ratio: float
    num_comments: int
    created_utc: float
    permalink: str
    url: str
    selftext: str = ""
    domain: str = ""
    is_self: bool = False
    over_18: bool = False
    spoiler: bool = False
    stickied: bool = False
    locked: bool = False
    is_video: bool = False
    link_flair_text: str | None = None
    distinguished: str | None = None


class Comment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    author: str
    body: str
    score: int
    created_utc: float
    permalink: str = ""
    depth: int = 0
    is_submitter: bool = False
    stickied: bool = False
    edited: bool | float = False
    parent_id: str = ""
    distinguished: str | None = None
    replies: list["Comment"] = Field(default_factory=list)


class SubredditInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    display_name: str
    title: str
    public_description: str = ""
    description: str = ""
    subscribers: int = 0
    active_user_count: int | None = None
    created_utc: float = 0.0
    over18: bool = False
    subreddit_type: str = "public"
    lang: str = "en"
    url: str = ""
    quarantine: bool = False


class UserInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    created_utc: float
    link_karma: int = 0
    comment_karma: int = 0
    total_karma: int = 0
    is_gold: bool = False
    is_mod: bool = False
    is_employee: bool = False
    has_verified_email: bool = False
    icon_img: str | None = None


class PostDetail(BaseModel):
    post: Post
    comments: list[Comment | dict] = Field(default_factory=list)


class Listing(BaseModel):
    posts: list[Post]
    after: str | None = None
    count: int = 0


class CLIError(BaseModel):
    code: int
    message: str
    detail: str | None = None
