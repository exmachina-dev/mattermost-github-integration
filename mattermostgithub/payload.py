from io import BytesIO
import requests
from mattermostgithub.config import SHOW_AVATARS
try:
    from PIL import Image
except ImportError:
    SHOW_AVATARS = False

class Payload(object):
    def __init__(self, data):
        self.data = data

    def user_link(self, data=None):
        if not data:
            data = self.data['sender']
        name   = data['login']
        url    = data['html_url']
        avatar = data['avatar_url'] + "&s=18"
        return self.create_user_link(name, url, avatar)

    def check_avatar_size(self, url):
        f = requests.get(url)
        img = Image.open(BytesIO(f.content))
        f.close()
        if img.size[0] <= 20 and img.size[1] <= 20:
            return True
        return False

    def create_user_link(self, name, url, avatar):
        if SHOW_AVATARS and self.check_avatar_size(avatar):
            return "![](%s) [%s](%s)" % (avatar, name, url)
        return "[%s](%s)" % (name, url)

    def repo_link(self):
        name = self.data['repository']['full_name']
        url  = self.data['repository']['html_url']
        return "[%s](%s)" % (name, url)

    def organization_link(self):
        name = self.data['organization']['login']
        url  = self.data['organization']['url']
        if SHOW_AVATARS and self.check_avatar_size(self.data['organization']['avatar_url']):
            avatar = self.data['organization']['avatar_url']
            return "![](%s) [%s](%s)" % (avatar, name, url)
        return "[%s](%s)" % (name, url)

    def preview(self, text, sep='\n', max_len=500, suffix=' [...]'):
        if not text:
            return text


        lines = text.splitlines()
        if len(lines) <= 1:
            return text

        text_len = 0
        sep_len = len(sep)
        suffix_len = len(suffix)
        result = []
        for l in lines:
            if text_len + len(l) < (max_len - suffix_len):
                result.append(l)
                text_len += len(l) + sep_len
            else:
                l_len = max_len - text_len - suffix_len
                if l_len <= 0:
                    result.append(suffix)
                else:
                    result.append(l[:l_len] + suffix)
                break

        return sep.join(result)


class PullRequest(Payload):
    def __init__(self, data):
        Payload.__init__(self, data)
        self.number = self.data['pull_request']['number']
        self.title  = self.data['pull_request']['title']
        self.body   = self.data['pull_request']['body']
        self.url    = self.data['pull_request']['html_url']

    def opened(self):
        body = self.preview(self.body, sep='\n> ')
        msg = """%s opened new pull request [#%s %s](%s) in %s:
> %s""" % (self.user_link(), self.number, self.title,
            self.url, self.repo_link(), body)
        return msg

    def assigned(self):
        to_name   = self.data['assignee']['login']
        to_url    = self.data['assignee']['html_url']
        to_avatar = self.data['assignee']['avatar_url'] + "&s=18"
        to = self.create_user_link(to_name, to_url, to_avatar)
        msg = """%s assigned %s to pull request [#%s %s](%s).""" % (self.user_link(),
            to, self.number, self.title, self.url)
        return msg

    def closed(self):
        merged = self.data['pull_request']['merged']
        action = "merged" if merged else "closed"
        msg = """%s %s pull request [#%s %s](%s).""" % (self.user_link(),
            action, self.number, self.title, self.url)
        return msg

    def synchronize(self):
        msg = """%s modified pull request [#%s %s](%s).""" % (self.user_link(),
            self.number, self.title, self.url)
        return msg

class PullRequestComment(Payload):
    def __init__(self, data):
        Payload.__init__(self, data)
        self.number = self.data['pull_request']['number']
        self.title  = self.data['pull_request']['title']
        self.body   = self.data['comment']['body']
        self.url    = self.data['comment']['html_url']

    def created(self):
        body = self.preview(self.body, sep='\n> ')
        msg = """%s commented on pull request [#%s %s](%s):
> %s""" % (self.user_link(), self.number, self.title, self.url, body)
        return msg

class Issue(Payload):
    def __init__(self, data):
        Payload.__init__(self, data)
        self.number = self.data['issue']['number']
        self.title  = self.data['issue']['title']
        self.url    = self.data['issue']['html_url']
        self.body   = self.data['issue']['body']

    def opened(self):
        body = '> ' + self.preview(self.body, sep='\n> ')
        msg = []
        msg.append("%s opened new issue [#%s %s](%s) in %s:" % (
                   self.user_link(), self.number, self.title,
                   self.url, self.repo_link()))
        return '\n'.join(msg)

    def labeled(self):
        label = self.data['label']['name']
        msg = """%s added label `%s` to issue [#%s %s](%s) in %s.""" % (self.user_link(), label, self.number, self.title, self.url, self.repo_link())
        return msg

    def closed(self):
        msg = """%s closed issue [#%s %s](%s) in %s.""" % (self.user_link(), self.number, self.title, self.url, self.repo_link())
        return msg

    def assigned(self):
        name   = self.data['assignee']['login']
        url    = self.data['assignee']['html_url']
        avatar = self.data['assignee']['avatar_url'] + "&s=18"
        assignee = self.create_user_link(name, url, avatar)
        msg = """%s assigned %s to issue [#%s %s](%s) in %s.""" % (self.user_link(), assignee, self.number, self.title, self.url, self.repo_link())
        return msg

class IssueComment(Payload):
    def __init__(self, data):
        Payload.__init__(self, data)
        self.number = self.data['issue']['number']
        self.title  = self.data['issue']['title']
        self.url    = self.data['comment']['html_url']
        self.body   = self.data['comment']['body']

    def created(self):
        body = '> ' + self.preview(self.body, sep='\n> ')
        msg = []
        msg.append("%s commented on [#%s %s](%s):" % (self.user_link(), self.number, self.title, self.url))
        msg.append(body)
        return '\n'.join(msg)

class CommitComment(Payload):
    def __init__(self, data):
        Payload.__init__(self, data)
        self.cid    = self.data['comment']['commit_id'][:7]
        self.url    = self.data['comment']['html_url']
        self.body   = self.data['comment']['body']

    def created(self):
        body = self.preview(self.body, sep='\n> ')
        msg = """%s commented on [%s](%s):
> %s""" % (self.user_link(), self.cid, self.url, body)
        return msg

class Repository(Payload):
    def __init__(self, data):
        Payload.__init__(self, data)

    def created(self):
        descr = self.data['repository']['description']
        msg = """%s created new repository %s:
> %s""" % (self.user_link(), self.repo_link(), descr)
        return msg

class Branch(Payload):
    def __init__(self, data):
        Payload.__init__(self, data)
        self.name = self.data['ref']

    def created(self):
        msg = """%s added branch `%s` to %s.""" % (self.user_link(),
            self.name, self.repo_link())
        return msg

    def deleted(self):
        msg = """%s deleted branch `%s` in %s.""" % (self.user_link(),
            self.name, self.repo_link())
        return msg

class Tag(Payload):
    def __init__(self, data):
        Payload.__init__(self, data)
        self.name = self.data['ref']

    def created(self):
        msg = """%s added tag `%s` to %s.""" % (self.user_link(),
            self.name, self.repo_link())
        return msg

class Push(Payload):
    def __init__(self, data):
        Payload.__init__(self, data)

    def author_link(self, data):
        name   = data['name']
        if data.get('username', False):
            url = 'https://github.com/' + data['username']
            avatar = url + '.png'
            if SHOW_AVATARS:
                return "![](%s =18) [%s](%s)" % (avatar, name, url)
            return "[%s](%s)" % (name, url)
        else:
            return name

    def commits(self):
        commits = self.data['commits']
        branch = self.data['ref'].replace("refs/heads/", "")
        branch_url = self.data['repository']['html_url'] + "/tree/" + branch
        if not commits:
            commits = [self.data['head_commit']]
        changeset = "changesets" if len(commits) > 1 else "changeset"
        msg = []
        msg.append("%s pushed %s %s to [%s](%s) at %s:" % (self.user_link(), len(commits), changeset, branch, branch_url, self.repo_link()))
        for commit in commits:
            cid  = commit['id'][:7]
            curl = commit['url']
            cmsg = self.preview(commit['message'], sep='\n  ')
            ctext = "- [`%s`](%s) by %s: %s" % (cid, curl, self.author_link(commit['author']), cmsg)
            msg.append("\n")
            msg.append(ctext)
        return "".join(msg)

class Wiki(Payload):
    def __init__(self, data):
        Payload.__init__(self, data)

    def updated(self):
        pages = self.data['pages']

        msg = []
        msg.append("%s changes %s pages in Wiki at %s:" % (self.user_link(), len(pages), self.repo_link()))
        for page in pages:
            page_name  = page['page_name']
            title = page['title']
            summary = page['summary']
            url = "%s/_compare/%s" % (page['html_url'], page['sha'])
            action = page['action']
            if summary :
              ctext = "- %s [%s](%s)\n>%s" % (action, page_name, url,summary)
            else :
              ctext = "- %s [%s](%s)\n" % (action, page_name, url)
            msg.append("\n")
            msg.append(ctext)
        return "".join(msg)


class Deployment(Payload):
    def __init__(self, data):
        Payload.__init__(self, data)

    def deploy(self):
        msg = "Deploying %s at  %s thanks to %s." % (self.data['deployment']['ref'], self.repo_link(), self.user_link(self.data['deployment']['creator']))
        return msg


class DeploymentStatus(Payload):
    def __init__(self, data):
        Payload.__init__(self, data)

    def deployment_link(self):
        name = self.data['deployment']['id']
        url =  self.data['deployment']['url']
        return '[#%s](%s)' % (name, url)
    def success(self):
        msg = "Deployment %s at  %s triggered by %s succeded :metal:." % (
                self.deployment_link(), self.repo_link(), self.user_link())
        return msg

    def pending(self):
        msg = "Deployment %s at  %s triggered by %s is still pending." % (
                self.deployment_link(), self.repo_link(), self.user_link())
        return msg

    def error(self):
        msg = "Deployment %s at  %s triggered by %s errored:\n%s" % (
                self.deployment_link(), self.repo_link(), self.user_link(),
                self.data['deployment_status']['description'] or '')
        return msg

    def failed(self):
        msg = "Deployment %s at  %s triggered by %s is failed like :shit::\n%s" % (
                self.deployment_link(), self.repo_link(), self.user_link(),
                self.data['deployment_status']['description'] or '')
        return msg


class Organization(Payload):
    def __init__(self, data):
        Payload.__init__(self, data)

    def member_added(self):
        msg = '%s has been added to %s' % (
                self.user_link(self.data['membership']['user']), self.organization_link())
        return msg

    def member_removed(self):
        msg = '%s has been removed to %s' % (
                self.user_link(self.data['membership']['user']), self.organization_link())
        return msg

    def member_invited(self):
        msg = "%s has been invited to join %s." % (
                self.data['invitation']['login'], self.organization_link())
        return msg
