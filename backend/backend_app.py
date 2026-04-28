import logging
from itertools import count

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

limiter = Limiter(app=app, key_func=get_remote_address,
                  default_limits=["100 per hour"])  # configure limiter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

POSTS = []
categories = ["Programming", "Tech", "Tutorial", "Backend"]
tags_pool = ["python", "flask", "api", "web", "backend", "coding"]

for i in range(1, 51):
    post_example = {
        "id": i,
        "title": f"Post {i}",
        "content": f"This is the content of post {i}",
        "category": categories[i % len(categories)],
        "tags": [tags_pool[i % len(tags_pool)], tags_pool[(i + 1) % len(tags_pool)]],
        "comments": [
            {"id": 1, "text": f"Comment 1 on post {i}"},
            {"id": 2, "text": f"Comment 2 on post {i}"}
        ]
    }
    POSTS.append(post_example)

post_id_counter = count(start=len(POSTS) + 1)


def find_post_by_id(post_id):
    """ Find the post with the id `post_id`.
    If there is no post with this id, return None. """
    for post in POSTS:
        if post["id"] == post_id:
            return post
    return None


def validate_post_data(data):
    """
    validate the post data
    :param data: post data dictionary
    :return: True if post data is valid, False otherwise
    """
    if not data or "title" not in data or "content" not in data:
        return False
    return True


def pagination_posts(posts):
    """
    paginate the posts
    :param posts: all posts
    :return: paginated posts
    """
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
    except ValueError:
        return posts

    if page < 1 or limit < 1:
        return posts

    start_index = (page - 1) * limit
    end_index = start_index + limit

    return posts[start_index:end_index]


@app.route('/api/posts', methods=['GET'])
@limiter.limit("10/minute")  # Limit to 10 requests per m
def get_posts_v1():
    """
    get all posts
    :return: jsonify of all posts
    """
    app.logger.info('GET request received for /api/posts')  # Log a message

    sort = request.args.get('sort') or None
    direction = request.args.get('direction', 'asc')

    if sort:
        sort = sort.lower()
    if direction:
        direction = direction.lower()

    if sort and sort not in ["title", "content"]:
        return jsonify({"error": "Invalid sort", "version": "v1"}), 400

    if direction not in ["asc", "desc"]:
        return jsonify({"error": "Invalid direction", "version": "v1"}), 400

    reverse = True if direction == "desc" else False

    sorted_posts = POSTS.copy()

    if sort in ["title", "content"]:
        sorted_posts.sort(
            key=lambda post: post.get(sort, ""),
            reverse=reverse
        )

    paginated_posts = pagination_posts(sorted_posts)

    return jsonify({"data": paginated_posts, "version": "v1"}), 200


@app.route('/api/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """
    get a post with id = post_id from the database
    :param post_id: id of the post
    :return: jsonify of a post
    """
    app.logger.info(f'GET request received for /api/posts/{post_id}')  # Log a message

    post = find_post_by_id(post_id)

    # If the post wasn't found, return a 404 error
    if post is None:
        return '', 404

    return jsonify({"data": post, "version": "v1"}), 200


@app.route('/api/posts', methods=['POST'])
def add_post():
    """
    add a post to the database
    :return: jsonify of all posts including a new post
    """
    app.logger.info('POST request received for /api/posts')  # Log a message

    new_post = request.get_json()
    if not validate_post_data(new_post):
        return jsonify({"error": "Invalid post data", "version": "v1"}), 400

    post = {
        "id": next(post_id_counter),
        "title": new_post.get("title"),
        "content": new_post.get("content"),
        "category": new_post.get("category", "General"),
        "tags": new_post.get("tags", []),
        "comments": new_post.get("comments", [])
    }
    POSTS.append(post)
    return jsonify({"data": post, "version": "v1"}), 201


@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    """
    delete a post from the database
    :param post_id:
    :return: the deleted post
    """
    app.logger.info(f'DELETE request received for /api/posts/{post_id}')  # Log a message

    post = find_post_by_id(post_id)

    if post is None:
        return jsonify({"error": "Invalid post id", "version": "v1"}), 404

    POSTS.remove(post)

    return jsonify({"message": f"Post with id {post_id} has been deleted successfully.", "version": "v1"}), 200


@app.route('/api/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id):
    """
    update a post from the database
    :param post_id: post id
    :return: post with updated data
    """
    app.logger.info(f'PUT request received for /api/posts/{post_id}')  # Log a message

    post = find_post_by_id(post_id)
    if post is None:
        return jsonify({"error": "Invalid post id", "version": "v1"}), 404

    new_data = request.get_json() or {}
    if "title" in new_data:
        post["title"] = new_data["title"]
    if "content" in new_data:
        post["content"] = new_data["content"]
    if "category" in new_data:
        post["category"] = new_data["category"]

    return jsonify({"data": post, "version": "v1"}), 200


@app.route('/api/posts/search', methods=['GET'])
def search_posts():
    """
    search posts
    :return: jsonify of all matching posts
    """
    app.logger.info(f'GET request received for /api/posts/search')  # Log a message

    title = request.args.get('title') or None
    content = request.args.get('content') or None

    filter_posts = [
        post for post in POSTS
        if (not title or title.lower() in post.get("title", "").lower())
           and (not content or content.lower() in post.get("content", "").lower())
    ]

    paginated_posts = pagination_posts(filter_posts)

    return jsonify({"data": paginated_posts, "version": "v1"}), 200


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=True)
