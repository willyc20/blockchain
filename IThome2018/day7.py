# -*- coding: utf-8 -*-

import socket
import struct
import threading
import time
import traceback
import ecdsa
import copy
import hashlib
import random
import json


# 區塊鏈的第一個區塊在術語中叫做創世區塊(Genesis block)
# 一開始就要有了 不然後面加進來的區塊沒東西連
Genesis_block = {
    'prev_Hash': '',
    'nonce': '',
    'timestamp': 0, 
    'Txs': [ # 一個block裡面會有很多個transaction紀錄
        # 假設一筆transaction
        # 有個叫小明的一開始有1000萬
        {  
            'owner_vk': '-----BEGIN PUBLIC KEY-----\nMFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAEZUBDWMgG3dTAzKcvMbw1IkJiLbtFq/Ay\nLIMsKpz2v2mc3e3QJUM/scURMzoXPDSPftfU2CT6f4K0saWZsstAWg==\n-----END PUBLIC KEY-----', # 小明的公鑰
            'preowner_vk': '先假設整個網路都認可',
            'data': '放了1000萬',
            'signature': '先假設整個網路都認可'
        }
    ] 
}


def btdebug( msg ):
    """ Prints a messsage to the screen with the name of the current thread """
    print "[%s] %s" % ( str(threading.currentThread().getName()), msg )


#==============================================================================
class BTPeer:
    """ Implements the core functionality that might be used by a peer in a
    P2P network.

    """

    #--------------------------------------------------------------------------
    def __init__( self, maxpeers, serverport, myid=None, serverhost = None ):
    #--------------------------------------------------------------------------
        """ Initializes a peer servent (sic.) with the ability to catalog
        information for up to maxpeers number of peers (maxpeers may
        be set to 0 to allow unlimited number of peers), listening on
        a given server port , with a given canonical peer name (id)
        and host address. If not supplied, the host address
        (serverhost) will be determined by attempting to connect to an
        Internet host like Google.

        """
        self.debug = 0

        self.maxpeers = int(maxpeers)
        self.serverport = int(serverport)
        if serverhost: self.serverhost = serverhost
        else: self.__initserverhost()

        if myid: self.myid = myid
        else: self.myid = '%s:%d' % (self.serverhost, self.serverport)

        self.peerlock = threading.Lock()  # ensure proper access to
                                    # peers list (maybe better to use
                                    # threading.RLock (reentrant))
        self.peers = {}        # peerid ==> (host, port) mapping
        self.shutdown = False  # used to stop the main loop

        self.handlers = {}

        self.addhandler('RETR', self.recv_tran)
        self.addhandler('REBL', self.recv_block)
        self.router = None

        self.blockchain = [Genesis_block]

    #--------------------------------------------------------------------------
    def __initserverhost( self ):
    #--------------------------------------------------------------------------
        """ Attempt to connect to an Internet host in order to determine the
        local machine's IP address.

        """
        s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        s.connect( ( "www.google.com", 80 ) )
        self.serverhost = s.getsockname()[0]
        s.close()



    #--------------------------------------------------------------------------
    def __debug( self, msg ):
    #--------------------------------------------------------------------------
        if self.debug:
            btdebug( msg )



    #--------------------------------------------------------------------------
    def __handlepeer( self, clientsock ):
    #--------------------------------------------------------------------------
        """
        handlepeer( new socket connection ) -> ()

        Dispatches messages from the socket connection
        """

        self.__debug( 'New child ' + str(threading.currentThread().getName()) )
        self.__debug( 'Connected ' + str(clientsock.getpeername()) )

        host, port = clientsock.getpeername()
        peerconn = BTPeerConnection( None, host, port, clientsock, debug=False )
        
        try:
            msgtype, msgdata = peerconn.recvdata()
            if msgtype: msgtype = msgtype.upper()
            if msgtype not in self.handlers:
                self.__debug( 'Not handled: %s: %s' % (msgtype, msgdata) )
            else:
                self.__debug( 'Handling peer msg: %s: %s' % (msgtype, msgdata) )
                self.handlers[ msgtype ]( peerconn, msgdata )
        except KeyboardInterrupt:
            raise
        except:
            if self.debug:
                traceback.print_exc()
        
        self.__debug( 'Disconnecting ' + str(clientsock.getpeername()) )
        peerconn.close()

    # end handlepeer method



    #--------------------------------------------------------------------------
    def __runstabilizer( self, stabilizer, delay ):
    #--------------------------------------------------------------------------
        while not self.shutdown:
            stabilizer()
            time.sleep( delay )

            

    #--------------------------------------------------------------------------
    def setmyid( self, myid ):
    #--------------------------------------------------------------------------
        self.myid = myid



    #--------------------------------------------------------------------------
    def startstabilizer( self, stabilizer, delay ):
    #--------------------------------------------------------------------------
        """ Registers and starts a stabilizer function with this peer. 
        The function will be activated every <delay> seconds. 

        """
        t = threading.Thread( target = self.__runstabilizer, 
                              args = [ stabilizer, delay ] )
        t.start()

        

    #--------------------------------------------------------------------------
    def addhandler( self, msgtype, handler ):
    #--------------------------------------------------------------------------
        """ Registers the handler for the given message type with this peer """
        assert len(msgtype) == 4
        self.handlers[ msgtype ] = handler



    #--------------------------------------------------------------------------
    def addrouter( self, router ):
    #--------------------------------------------------------------------------
        """ Registers a routing function with this peer. The setup of routing
        is as follows: This peer maintains a list of other known peers
        (in self.peers). The routing function should take the name of
        a peer (which may not necessarily be present in self.peers)
        and decide which of the known peers a message should be routed
        to next in order to (hopefully) reach the desired peer. The router
        function should return a tuple of three values: (next-peer-id, host,
        port). If the message cannot be routed, the next-peer-id should be
        None.

        """
        self.router = router



    #--------------------------------------------------------------------------
    def addpeer( self, peerid, host, port ):
    #--------------------------------------------------------------------------
        """ Adds a peer name and host:port mapping to the known list of peers.
        
        """
        if peerid not in self.peers and (self.maxpeers == 0 or
                                         len(self.peers) < self.maxpeers):
            self.peers[ peerid ] = (host, int(port))
            return True
        else:
            return False



    #--------------------------------------------------------------------------
    def getpeer( self, peerid ):
    #--------------------------------------------------------------------------
        """ Returns the (host, port) tuple for the given peer name """
        assert peerid in self.peers    # maybe make this just a return NULL?
        return self.peers[ peerid ]




    #--------------------------------------------------------------------------
    def removepeer( self, peerid ):
    #--------------------------------------------------------------------------
        """ Removes peer information from the known list of peers. """
        if peerid in self.peers:
            del self.peers[ peerid ]


    #--------------------------------------------------------------------------
    def makeserversocket( self, port, backlog=5 ):
    #--------------------------------------------------------------------------
        """ Constructs and prepares a server socket listening on the given 
        port.

        """
        s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        s.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
        s.bind( ( '', port ) )
        s.listen( backlog )
        return s



    #--------------------------------------------------------------------------
    def sendtopeer( self, peerid, msgtype, msgdata, waitreply=True ):
    #--------------------------------------------------------------------------
        """
        sendtopeer( peer id, message type, message data, wait for a reply )
         -> [ ( reply type, reply data ), ... ] 

        Send a message to the identified peer. In order to decide how to
        send the message, the router handler for this peer will be called.
        If no router function has been registered, it will not work. The
        router function should provide the next immediate peer to whom the 
        message should be forwarded. The peer's reply, if it is expected, 
        will be returned.

        Returns None if the message could not be routed.
        """

        if self.router:
            nextpid, host, port = self.router( peerid )
        if not self.router or not nextpid:
            self.__debug( 'Unable to route %s to %s' % (msgtype, peerid) )
            return None
        #host,port = self.peers[nextpid]
        return self.connectandsend( host, port, msgtype, msgdata,
                                    pid=nextpid,
                                    waitreply=waitreply )
    


    #--------------------------------------------------------------------------
    def connectandsend( self, host, port, msgtype, msgdata, 
                        pid=None, waitreply=True ):
    #--------------------------------------------------------------------------
        """
        connectandsend( host, port, message type, message data, peer id,
        wait for a reply ) -> [ ( reply type, reply data ), ... ]

        Connects and sends a message to the specified host:port. The host's
        reply, if expected, will be returned as a list of tuples.

        """
        msgreply = []
        try:
            peerconn = BTPeerConnection( pid, host, port, debug=self.debug )
            peerconn.senddata( msgtype, msgdata )
            self.__debug( 'Sent %s: %s' % (pid, msgtype) )
            
            if waitreply:
                onereply = peerconn.recvdata()
                while (onereply != (None,None)):
                    msgreply.append( onereply )
                    self.__debug( 'Got reply %s: %s' 
                                  % ( pid, str(msgreply) ) )
                    onereply = peerconn.recvdata()
            peerconn.close()
        except KeyboardInterrupt:
            raise
        except:
            if self.debug:
                traceback.print_exc()
        
        return msgreply

    # end connectsend method



    #--------------------------------------------------------------------------
    def checklivepeers( self ):
    #--------------------------------------------------------------------------
        """ Attempts to ping all currently known peers in order to ensure that
        they are still active. Removes any from the peer list that do
        not reply. This function can be used as a simple stabilizer.

        """
        todelete = []
        for pid in self.peers:
            isconnected = False
            try:
                self.__debug( 'Check live %s' % pid )
                host,port = self.peers[pid]
                peerconn = BTPeerConnection( pid, host, port, debug=self.debug )
                peerconn.senddata( 'PING', '' )
                isconnected = True
            except:
                todelete.append( pid )
            if isconnected:
                peerconn.close()

        self.peerlock.acquire()
        try:
            for pid in todelete: 
                if pid in self.peers: del self.peers[pid]
        finally:
            self.peerlock.release()
    # end checklivepeers method

    def recv_block( self , peerconn, msgdata):
        new_block = json.loads(msgdata)

        # 先確定區塊的合法性
        # 才能確定區塊是不是算力大的一方來的
        if new_block['timestamp'] < self.blockchain[-1]['timestamp']:
            print("node %s:區塊不合法，應按照時間生成" % self.myid)
            return

        if new_block['pre_Hash'] != hashlib.sha256(str(self.blockchain[-1])).hexdigest():
            print("node %s:區塊不合法，前一個hash值對不起來" % self.myid)
            return

        if hashlib.sha256(str(new_block).decode('utf-8')).hexdigest()[0:4] != '0000':
            print("node %s:區塊不合法，hash值不符合proof of work的規定" % self.myid)
            return

        check_legel = True
        # 第j的區塊的第k個transaction
        for j in range(len(self.blockchain)):
            for k in range(len(self.blockchain[j]['Txs'])):
                for l in range(len(new_block['Txs'])):
                    if self.blockchain[j]['Txs'][k]['preowner_vk'].decode('utf-8') == new_block['Txs'][l]['preowner_vk'].decode('utf-8'):
                        check_legel = False


        if check_legel == True:
            self.blockchain.append(new_block)
            print("node %s:紀錄了新block中的所有交易" % self.myid)
        else:
            print("node %s:抱歉，這筆交易不合規定，不能重複交易" % self.myid)

    # 將區塊昭告天下
    def block_broadcast(self, new_block):
    
        todelete = []
        for pid in self.peers:
            isconnected = False
            try:
                self.__debug( 'Check live %s' % pid )
                host,port = self.peers[pid]
                peerconn = BTPeerConnection( pid, host, port, debug=self.debug )
                peerconn.senddata( 'REBL', json.dumps(new_block, encoding='latin1') )
                isconnected = True
            except:
                todelete.append( pid )
            if isconnected:
                peerconn.close()

        self.peerlock.acquire()
        try:
            for pid in todelete: 
                if pid in self.peers: del self.peers[pid]
        finally:
            self.peerlock.release()


    # try到適合的Nonce來讓該區塊合法
    def proof_of_work(self, block):

        # 區塊的產生時間應該按照順序
        if block['timestamp'] < self.blockchain[-1]['timestamp']:
            print('區塊不合法')
            return

        block['pre_Hash'] = hashlib.sha256(str(self.blockchain[-1]).decode('utf-8')).hexdigest()
        # 這裡都當作required zero有32bit
        # required zero只是論文中為了說明概念使用
        # 真正的難度在現實應用中會根據前一個block的計算時間之類的動態調整
        # 實際應用上是要讓hsah小於某個值才算合法 不然真的都用required zero難度只能一次調2的次方
        while True:
            block['nonce'] = random.randint(-214783648, 2147483647)
        
            if hashlib.sha256(str(json.loads(json.dumps(block))).decode('utf-8')).hexdigest()[0:4] == '0000':
                print('%s 計算合法區塊成功' % self.myid)
                self.block_broadcast(block)
                return


    def recv_tran( self , peerconn, msgdata):

        block = {
            'prev_Hash': None,
            'nonce': None,
            'timestamp': int(time.time()), 
            'Txs': []
        }
        block['Txs'].append(json.loads(msgdata))
        self.proof_of_work(block)



    # 談好一筆交易了
    def trade_broadcast(self, pre_tran, data, pre_sk, now_vk):
        
        transaction = {
            'owner_vk': now_vk,
            'preowner_vk': pre_tran['owner_vk'],
            'data': data,
            'signature': ecdsa.SigningKey.from_pem(pre_sk).sign(str(pre_tran)+now_vk)
        }           

        try:
            # 交易談好了
            # 現在確認上一個transaction的擁有者有沒有偷改他以前的交易內容
            
            ecdsa.VerifyingKey.from_pem(pre_tran['owner_vk']).verify(transaction['signature'], str(pre_tran) + now_vk)
            todelete = []
            for pid in self.peers:
                isconnected = False
                try:
                    self.__debug( 'Check live %s' % pid )
                    host,port = self.peers[pid]
                    peerconn = BTPeerConnection( pid, host, port, debug=self.debug )
                    peerconn.senddata( 'RETR',  json.dumps(transaction, encoding='latin1'))
                    isconnected = True
                except:
                    todelete.append( pid )
                if isconnected:
                    peerconn.close()

            self.peerlock.acquire()
            try:
                for pid in todelete: 
                    if pid in self.peers: del self.peers[pid]
            finally:
                self.peerlock.release()
        except:
            print('有騙子?!')

        
    # end checklivepeers method


    #--------------------------------------------------------------------------
    def mainloop( self ):
    #--------------------------------------------------------------------------


        s = self.makeserversocket( self.serverport )
        s.settimeout(2)
        self.__debug( 'Server started: %s (%s:%d)'
                      % ( self.myid, self.serverhost, self.serverport ) )
        
        while not self.shutdown:
            try:
                self.__debug( 'Listening for connections...' )
                clientsock, clientaddr = s.accept()
                clientsock.settimeout(None)

                t = threading.Thread( target = self.__handlepeer,
                                      args = [ clientsock ] )
                t.start()
            except KeyboardInterrupt:
                print 'KeyboardInterrupt: stopping mainloop'
                self.shutdown = True
                continue
            except:
                if self.debug:
                    traceback.print_exc()
                    continue

        # end while loop
        self.__debug( 'Main loop exiting' )

        s.close()


    # end mainloop method

# end BTPeer class




# **********************************************************




class BTPeerConnection:

    #--------------------------------------------------------------------------
    def __init__( self, peerid, host, port, sock=None, debug=False ):
    #--------------------------------------------------------------------------
        # any exceptions thrown upwards

        self.id = peerid
        self.debug = debug

        if not sock:
            self.s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
            self.s.connect( ( host, int(port) ) )
        else:
            self.s = sock

        self.sd = self.s.makefile( 'rw', 0 )


    #--------------------------------------------------------------------------
    def __makemsg( self, msgtype, msgdata ):
    #--------------------------------------------------------------------------
        msglen = len(msgdata)
        msg = struct.pack( "!4sL%ds" % msglen, msgtype, msglen, msgdata )
        return msg


    #--------------------------------------------------------------------------
    def __debug( self, msg ):
    #--------------------------------------------------------------------------
        if self.debug:
            btdebug( msg )


    #--------------------------------------------------------------------------
    def senddata( self, msgtype, msgdata ):
    #--------------------------------------------------------------------------
        """
        senddata( message type, message data ) -> boolean status

        Send a message through a peer connection. Returns True on success
        or False if there was an error.
        """

        try:
            msg = self.__makemsg( msgtype, msgdata )
            self.sd.write( msg )
            self.sd.flush()
        except KeyboardInterrupt:
            raise
        except:
            if self.debug:
                traceback.print_exc()
            return False
        return True
            

    #--------------------------------------------------------------------------
    def recvdata( self ):
    #--------------------------------------------------------------------------
        """
        recvdata() -> (msgtype, msgdata)

        Receive a message from a peer connection. Returns (None, None)
        if there was any error.
        """

        try:
            msgtype = self.sd.read( 4 )
            if not msgtype: return (None, None)
            
            lenstr = self.sd.read( 4 )
            msglen = int(struct.unpack( "!L", lenstr )[0])
            msg = ""

            while len(msg) != msglen:
                data = self.sd.read( min(2048, msglen - len(msg)) )
                if not len(data):
                    break
                msg += data

            if len(msg) != msglen:
                return (None, None)

        except KeyboardInterrupt:
            raise
        except:
            if self.debug:
                traceback.print_exc()
            return (None, None)

        return ( msgtype, msg )

    # end recvdata method


    #--------------------------------------------------------------------------
    def close( self ):
    #--------------------------------------------------------------------------
        """
        close()

        Close the peer connection. The send and recv methods will not work
        after this call.
        """

        self.s.close()
        self.s = None
        self.sd = None


    #--------------------------------------------------------------------------
    def __str__( self ):
    #--------------------------------------------------------------------------
        return "|%s|" % peerid

node = BTPeer(0, 4446)
node.addpeer(1, 'xxx.xxx.xxx.xxx', 4444)
node.addpeer(2, 'xxx.xxx.xxx.xxx', 4445)
node.addpeer(3, 'xxx.xxx.xxx.xxx', 4446)

# 不厭其煩的強調，真實情境不要把在用的私鑰放到瀏覽器上
node.trade_broadcast(Genesis_block['Txs'][0], '同一個1000萬拿去收好', '-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIGqXRqNjZns1TJ1CfayizUPcpZop00KWWj0+fOy/WwqtoAcGBSuBBAAK\noUQDQgAEZUBDWMgG3dTAzKcvMbw1IkJiLbtFq/AyLIMsKpz2v2mc3e3QJUM/scUR\nMzoXPDSPftfU2CT6f4K0saWZsstAWg==\n-----END EC PRIVATE KEY-----', 'ggg')

