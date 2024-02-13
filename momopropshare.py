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
        self.optimistic_unchoked = 10
        self.round = 0

    def requests(self, peers, history):
        def needed(i):
            return self.pieces[i] < self.conf.blocks_per_piece

        needed_pieces = list(filter(needed, list(range(len(self.pieces)))))
        random.shuffle(needed_pieces)

        logging.debug("%s here: still need pieces %s" % (self.id, needed_pieces))

        requests = []

        frequencies = {piece: 0 for piece in needed_pieces}
        for peer in peers:
            for piece in peer.available_pieces:
                if piece in frequencies:
                    frequencies[piece] += 1

        download_contributions = {}
        if history.current_round() > 0:
            for download in history.downloads[-1]:
                if download.from_id in download_contributions:
                    download_contributions[download.from_id] += download.blocks
                else:
                    download_contributions[download.from_id] = download.blocks

        peers_by_contribution = sorted(
            peers, key=lambda peer: download_contributions.get(peer.id, 0), reverse=True
        )

        random.shuffle(peers)

        for peer in peers_by_contribution:
            av_set = set(peer.available_pieces)
            isect = av_set.intersection(set(needed_pieces))
            isectlist = list(isect)
            random.shuffle(isectlist)
            isectlist.sort(key=lambda p: frequencies[p])
            n = min(self.max_requests, len(isectlist))
            for piece_id in isectlist[:n]:
                start_block = self.pieces[piece_id]
                r = Request(self.id, peer.id, piece_id, start_block)
                requests.append(r)

        return requests


    def uploads(self, requests, peers, history):
        round = history.current_round()
        logging.debug("%s again. It's round %d." % (self.id, round))

        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            return []

        download_contributions = {}

        if round > 0:
            for download in history.downloads[-1]:
                peer_id = download.from_id
                if peer_id not in download_contributions:
                    download_contributions[peer_id] = download.blocks
                else:
                    download_contributions[peer_id] += download.blocks

        total_downloaded = sum(download_contributions.values())

        # Allocate bandwidth proportionally
        chosen = []
        reserved_bw = self.up_bw * self.optimistic_unchoked // 100
        available_bw = self.up_bw - reserved_bw

        for req in requests:
            peer_id = req.requester_id
            chosen.append(peer_id)

        bws = even_split(self.up_bw, len(chosen))

        requested_peers = [req.requester_id for req in requests]
        contributions = [
            (peer_id, download_contributions.get(peer_id, 0))
            for peer_id in requested_peers
            if peer_id in download_contributions
        ]

        for peer_id, contribution in contributions:
            if total_downloaded > 0:
                peer_bw = available_bw * (contribution / total_downloaded)
            else:
                peer_bw = available_bw // len(contributions)
            chosen.append(Upload(self.id, peer_id, int(peer_bw)))

        unchoke_int = 3

        if round % unchoke_int == 0:
            optimistic_unchoke_peer = random.choice(
                [req.requester_id for req in requests if req.requester_id not in chosen]
            )
            chosen.append(Upload(self.id, optimistic_unchoke_peer, reserved_bw))
            bws = even_split(self.up_bw, len(chosen))
            uploads = [Upload(self.id, peer_id, bw) for (peer_id, bw) in zip(chosen, bws)]
        else:
            for req in requests:
                peer_id = req.requester_id
                chosen.append(Upload(self.id, peer_id, reserved_bw // len(requests)))
        return uploads        return uploads