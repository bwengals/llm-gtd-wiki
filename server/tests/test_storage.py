import boto3
import pytest
from moto import mock_aws

from llm_gtd_wiki.config import Config
from llm_gtd_wiki.storage import WikiError, WikiStorage


def _cfg(bucket: str) -> Config:
    return Config(
        cognito_user_pool_id="",
        cognito_client_id="",
        cognito_domain="",
        cognito_region="us-west-2",
        allowed_subs=frozenset(),
        auth_disabled=True,
        wiki_bucket=bucket,
    )


def _store():
    s3 = boto3.client("s3", region_name="us-west-2")
    s3.create_bucket(
        Bucket="wiki", CreateBucketConfiguration={"LocationConstraint": "us-west-2"}
    )
    return WikiStorage(_cfg("wiki"), client=s3)


@mock_aws
def test_read_write_list():
    st = _store()
    st.write("index.md", "# Index\n- a\n- b\n")
    assert "index.md" in st.list_files()
    assert st.read("index.md").startswith("# Index")
    with pytest.raises(WikiError):
        st.read("missing.md")


@mock_aws
def test_edit_matrix():
    st = _store()
    st.write("index.md", "# Index\n- alpha\n- beta\n")
    assert st.edit("index.md", "- alpha", "- ALPHA") == "edited index.md"
    assert "- ALPHA" in st.read("index.md")
    with pytest.raises(WikiError, match="not found"):
        st.edit("index.md", "nope", "x")
    st.write("dup.md", "x\nx\n")
    with pytest.raises(WikiError, match="occurs 2 times"):
        st.edit("dup.md", "x", "y")


@mock_aws
def test_guards():
    st = _store()
    with pytest.raises(WikiError):
        st.read("../secret")
    with pytest.raises(WikiError):
        st.write("raw/notes.md", "nope")
    # a leading slash is normalized (not an error) and lands at the relative key
    st.write("/abs.md", "ok")
    assert "abs.md" in st.list_files()


@mock_aws
def test_append_and_search():
    st = _store()
    st.append("inbox.md", "- buy stamps")
    st.append("inbox.md", "- call vet")
    body = st.read("inbox.md")
    assert "- buy stamps" in body and "- call vet" in body
    hits = st.search("vet")
    assert any("inbox.md" in h for h in hits)
    assert st.search("zzzzz") == []
