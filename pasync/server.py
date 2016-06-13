# -*- coding: utf-8 -*-

from SocketServer import TCPServer, StreamRequestHandler, ThreadingMixIn


class QHandler(StreamRequestHandler):

    def handle(self):
        self.data = self.request.recv(1024).strip()
        addr = self.request.getpeername()
        print 'Got connection from: ', addr
        self.wfile.write(self.data)


# Support multi threading
class QServer(ThreadingMixIn, TCPServer):
    pass


if __name__ == '__main__':
    host, port = "localhost", 1234
    server = QServer((host, port), QHandler)
    print "Start server at {}:{} ...".format(host, port)
    server.serve_forever()
