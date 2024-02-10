#!/usr/bin/python

# This is a slightly smarter version of the dummy peer.
# The setup script will copy it to create the versions you edit

import random
import logging

from messages import Upload, Request
from util import even_split
from peer import Peer
import heapq


class LessDummy(Peer):
    def post_init(self):
        print("post_init(): %s here!" % self.id)
        ##################################################################################
        # Declare any variables here that you want to be able to access in future rounds #
        ##################################################################################

        # This commented out code is and example of a python dictionsary,
        # which is a convenient way to store a value indexed by a particular "key"
        # self.dummy_state = dict()
        class LessDummy(Peer):
            def post_init(self):
                print("post_init(): %s here!" % self.id)

                # Declare any variables here that you want to be able to access in future rounds
                self.dummy_state = dict()
                self.dummy_state["cake"] = "lie"
                self.frequencies = {}
                self.pieces = []
                self.conf = None  # Configuration object for the client
                self.max_requests = (
                    0  # Maximum number of requests to send to other peers
                )
                self.available_pieces = (
                    set()
                )  # Set to store the pieces available to the peer
                self.downloads = []  # List to store the download history of the peer
                self.uploaded = 0  # Total amount of data uploaded by the peer
                self.downloaded = 0  # Total amount of data downloaded by the peer
                self.requests_sent = []  # List to store the requests sent by the peer
                self.uploads_received = (
                    []
                )  # List to store the uploads received by the peer
                self.choked_by = (
                    set()
                )  # Set to store the peers that have choked the peer
                self.interested_in = (
                    set()
                )  # Set to store the peers that the peer is interested in
                self.optimistic_unchoked = (
                    None  # Peer that is optimistically unchoked by the peer
                )
                self.round = 0  # Current round number

                # Add any additional variables or data structures as needed

    def requests(self, peers, history):
        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
        needed_pieces = list(filter(needed, list(range(len(self.pieces)))))
        # Symmetry breaking is good, it creates more opportunities to trade
        # Try commenting this out and see what happens to performance...
        random.shuffle(needed_pieces)

        np_set = set(needed_pieces)  # sets support fast intersection ops.

        logging.debug("%s here: still need pieces %s" % (self.id, needed_pieces))

        requests = []  # We'll put all the things we want here

        # count frequencies of all pieces that the other peers have
        # this will be useful for implementing rarest first
        ###########################################################
        # We added this                                           #
        ###########################################################

        for peer in peers:
            for piece in peer.available_pieces:
                if piece in self.frequencies:
                    self.frequencies[piece] += 1
                else:
                    self.frequencies[piece] = 1

        self.pieces = [(count, piece) for piece, count in self.frequencies.items()]
        heapq.heapify(self.pieces)

        requests = []
        while len(requests) < self.max_requests and self.pieces:
            _, piece_id = heapq.heappop(self.pieces)
            if piece_id in needed_pieces:
                start_block = self.pieces[piece_id]
                r = Request(self.id, peer.id, piece_id, start_block)
                requests.append(r)

        return requests

    def uploads(self, requests, peers, history):
        """
        requests -- a list of the requests for this peer for this round
        peers -- available info about all the peers
        history -- history for all previous rounds

        returns: list of Upload objects.

        In each round, this will be called after requests().
        """

        ##############################################################################
        # The code and suggestions here will get you started for the standard client #
        # You'll need to change things for the other clients                         #
        ##############################################################################

        round = history.current_round()
        logging.debug("%s again.  It's round %d." % (self.id, round))
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to this peer in
        # the previous round.

        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:
            logging.debug("Still here: uploading to a random peer")

            ########################################################################
            # The dummy client picks a single peer at random to unchoke.           #
            # You should decide a set of peers to unchoke accoring to the protocol #
            ########################################################################
            request = random.choice(requests)
            chosen = [request.requester_id]

            # Now that we have chosen who to unchoke, the standard client evenly shares
            # its bandwidth among them
            bws = even_split(self.up_bw, len(chosen))

        # create actual uploads out of the list of peer ids and bandwidths
        # You don't need to change this
        uploads = [Upload(self.id, peer_id, bw) for (peer_id, bw) in zip(chosen, bws)]

        return uploads
