import mimetypes

def get_media_type(file=None, url=None):
    """
    Detect media type (image / video / audio) from file or URL
    """
    mime = None

    if file:
        mime = file.content_type
    elif url:
        mime, _ = mimetypes.guess_type(url)

    if mime is None:
        return None

    if mime.startswith("image"):
        return "image"
    if mime.startswith("video"):
        return "video"
    if mime.startswith("audio"):
        return "audio"

    return None


