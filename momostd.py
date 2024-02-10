#!/usr/bin/python

# This is a slightly smarter version of the dummy peer.
# The setup script will copy it to create the versions you edit

import logging
import random

from messages import Request, Upload
from peer import Peer
from util import even_split


class LessDummy(Peer):
    def post_init(self):
        print("post_init(): %s here!" % self.id)

        # Declare any variables here that you want to be able to access in future rounds
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
        self.frequencies = {}
        self.pieces = []
        self.conf = None
        self.max_requests = 0
        self.available_pieces = set()
        self.downloads = []
        self.uploaded = 0
        self.downloaded = 0
        self.requests_sent = []
        self.uploads_received = []
        self.choked_by = set()
        self.interested_in = set()
        self.optimistic_unchoked = None
        self.round = 0

    def requests(self, peers, history):
        """
        peers: available info about the peers (who has what pieces)
        history: what's happened so far as far as this peer can see

        returns: a list of Request() objects

        This will be called after update_pieces() with the most recent state.
        """

        # Calculate the pieces you still need
        def needed(i):
            return self.pieces[i] < self.conf.blocks_per_piece

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
        frequencies = {}
        for peer in peers:
            for piece in peer.available_pieces:
                if piece in frequencies:
                    frequencies[piece] = frequencies[piece] + 1
                else:
                    frequencies[piece] = 1

        # request all available pieces from all peers!
        # (up to self.max_requests from each)
        #############################################################################
        # We adapted this code from dummy to implement rarest first                 #
        #############################################################################
        for peer in peers:
            av_set = set(peer.available_pieces)
            isect = av_set.intersection(np_set)
            n = int(min(self.max_requests, len(isect)))
            # More symmetry breaking -- ask for random pieces when tied.
            isectlist = list(isect)
            random.shuffle(isectlist)
            isectlist.sort(key=lambda p: frequencies[p])
            for piece_id in isectlist[:n]:
                # aha! The peer has this piece! Request it.
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
