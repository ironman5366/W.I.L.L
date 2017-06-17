"""
Transactional methods to communicate with neo4j, using session objects
"""


def find_user(tx, username):
    """
    A neo4j callable to find a user and return their data
    Should be called with a read transaction

    :param tx: The neo4j-driver transaction object
    :param username: The username of the user that should be found
    """
    result = tx.run("MATCH (u:User {username: {username}})"
                    "return (u)",
                    {"username": username})
    return result


def get_user_client_rels(tx, client_id, username, step_rel):
    """
    Find the relationship a user has with a client.
    Should be called with a read transaction

    :param tx: The neo4j-driver transaction object
    :param client_id: The client id to look for
    :param username: The username to look for
    :param step_rel: The relationship to look for
    """
    result = tx.run("MATCH (:User {username: {username}})-[r:{step_rel}]->(:Client {client_id: {client_id}})"
                    "return (r)",
                    {"client_id": client_id,
                     "username": username,
                     "step_rel": step_rel})
    return result


def delete_rel(tx, rel_id, step_rel):
    """
    Delete a relationship using the id
    Should be called with a write transaction

    :param tx: The transaction object
    :param rel_id: The id of the relationship
    :param step_rel: The type of the relationship
    """
    tx.run("MATCH [r:{step_rel}] WHERE ID(r) = {rel_id}",
           {"step_rel": step_rel, "rel_id": rel_id})


def create_notification(tx, user, message, title, trigger_time, scope, created, summary, uid):
    """
    Cache a notification in the database
    Should be called with a write transaction

    :param tx: The transaction object
    :param user: The user that set the notification
    :param message: The message of the notification
    :param title: The title of the notification
    :param trigger_time: The time when the notification will be triggered
    :param scope: The scope, or method of sending, the notification
    :param created: The time at which the notification was created
    :param summary: The summary of the notification
    :param uid: The unique identifier of the notification
    """
    tx.run("MATCH (u:User {username: {username}})"
           "CREATE (n:Notification "
           "{uid: {uid},"
           "message: {message},"
           "title: {title},"
           "trigger_time: {trigger_time},"
           "scope: {scope},"
           "created: {created},"
           "summary: {summary}})"
           "MERGE (u)-[:SET]-(n)",
           {
                "username": user,
                "uid": uid,
                "message": message,
                "title": title,
                "trigger_time": trigger_time,
                "scope": scope,
                "created": created,
                "summary": summary
           })


def delete_notification(tx, not_uid):
    """
    Delete a notification from the db, using it's uid
    Should be called with a write transaction

    :param tx: The transaction object
    :param not_uid: The unique identifier of the notification
    """
    tx.run("MATCH (n:Notification {uid: {uid}})"
           "DETACH"
           "DELETE (n)",
           {"uid":  not_uid})