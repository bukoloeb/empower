# core/middleware.py
class VideoMimeTypeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # If the URL points to an mp4 in media, force the type
        if request.path.startswith('/media/') and request.path.endswith('.mp4'):
            response['Content-Type'] = 'video/mp4'
            response['Accept-Ranges'] = 'bytes'
        return response