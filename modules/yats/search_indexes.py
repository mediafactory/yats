# -*- coding: utf-8 -*-
from haystack import indexes
from yats.models import docs
from yats.shortcuts import get_ticket_model


class DocIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    caption = indexes.CharField(model_attr='caption')

    content_auto = indexes.EdgeNgramField(use_template=True)

    def prepare_caption(self, obj):
        return obj.caption[:245]

    def get_model(self):
        return docs

    def get_updated_field(self):
        return 'u_date'

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.filter(active_record=True)


class TicketIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True, template_name='search/indexes/yats/ticket_text.txt')
    caption = indexes.CharField(model_attr='caption')
    closed = indexes.BooleanField(model_attr='closed')
    last_action_date = indexes.DateTimeField(model_attr='last_action_date')
    customer = indexes.IntegerField(model_attr='customer_id')

    content_auto = indexes.EdgeNgramField(use_template=True, template_name='search/indexes/yats/ticket_content_auto.txt')

    def prepare_caption(self, obj):
        return obj.caption[:245]

    def get_model(self):
        return get_ticket_model()

    def get_updated_field(self):
        return 'last_action_date'

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.filter(active_record=True)
