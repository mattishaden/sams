#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# This file is part of SAMS.
#
# Copyright 2020 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from io import BytesIO
from behave import *
from flask import json
import hashlib
from werkzeug.http import unquote_etag
from zipfile import ZipFile

from tests.features.steps.helpers import assert_200, apply_placeholders, test_json, store_last_item, expect_status, \
    get_client_model_and_method_from_step
from tests.features.steps.app import get_app, get_client


@when('we send client.{model_name}.{method_name}')
def step_impl_send_client(context, model_name, method_name):
    client, model, method = get_client_model_and_method_from_step(
        context,
        model_name,
        method_name
    )

    kwargs = {} if not context.text else json.loads(apply_placeholders(context, context.text))
    context.response = method(**kwargs)
    store_last_item(context, model_name)


@when('we upload a binary file with client.{model_name}.{method_name}')
def step_impl_upload_binary_client(context, model_name, method_name):
    client, model, method = get_client_model_and_method_from_step(
        context,
        model_name,
        method_name
    )

    kwargs = {} if not context.text else json.loads(apply_placeholders(context, context.text))
    filename = kwargs.pop('filename', None)
    filepath = None if not filename else 'tests/fixtures/{}'.format(filename)
    files = None if not filepath else {'binary': open(filepath, 'rb')}

    context.response = method(files=files, **kwargs)
    store_last_item(context, model_name)


@when('we download a binary file with client.{model_name}.{method_name}')
def step_impl_download_binary_client(context, model_name, method_name):
    client, model, method = get_client_model_and_method_from_step(
        context,
        model_name,
        method_name
    )

    kwargs = {} if not context.text else json.loads(apply_placeholders(context, context.text))
    length = kwargs.pop('length', None)
    context.response = method(**kwargs)

    if context.response.status_code in [200, 201, 204] and length:
        response_etag, _ = unquote_etag(context.response.headers['ETag'])
        h = hashlib.sha1()
        h.update(context.response.content)
        expected_etag = h.hexdigest()
        assert response_etag == expected_etag, 'response.etag({}) != expected.etag({})'.format(
            response_etag,
            expected_etag
        )
        assert len(context.response.content) == length, 'response.length({}) != expected.length({})'.format(
            len(context.response.content),
            length
        )

        if method_name == 'get_binary_zip_by_id':
            zip_file = ZipFile(BytesIO(context.response.content))
            assert zip_file.testzip() is None

            item_ids = kwargs['item_ids']
            assets = client.assets.get_by_ids(item_ids).json()['_items']

            zip_filenames = zip_file.namelist()
            for asset in assets:
                assert asset['filename'] in zip_filenames


@when('we get "{url}"')
def step_impl_get(context, url: str):
    url = apply_placeholders(context, url)

    context.response = get_client(context).get(url=url)


@when('we post "{url}"')
def step_impl_post(context, url: str):
    url = apply_placeholders(context, url)
    data = None if not context.text else json.loads(apply_placeholders(context, context.text))

    context.response = get_client(context).post(
        url=url,
        data=data
    )


@when('we patch "{url}"')
def step_impl_post(context, url: str):
    url = apply_placeholders(context, url)
    data = None if not context.text else json.loads(apply_placeholders(context, context.text))

    context.response = get_client(context).patch(
        url=url,
        data=data
    )


@when('we delete "{url}"')
def step_impl_post(context, url: str):
    url = apply_placeholders(context, url)

    context.response = get_client(context).delete(url=url)


@then('we get OK response')
def step_impl_then_get_ok(context):
    assert_200(context.response)


@then('we get response code {code}')
def step_impl_then_get_code(context, code):
    assert context.response.status_code == int(code)


@then('we get error {code}')
def step_impl_then_get_error(context, code):
    expect_status(context.response, int(code))
    if context.text:
        test_json(context)


@then('we get existing resource')
def step_impl_then_get_existing(context):
    if not isinstance(context.response, tuple):
        assert_200(context.response)
    test_json(context)


@given('server config')
def step_impl_server_config(context):
    app = get_app(context)
    config = json.loads(apply_placeholders(context, context.text))
    app.init(config)
    app.start()
    context.app = app
    context._reset_after_scenario = True


@given('client config')
def step_impl_client_config(context):
    app = get_app(context)
    config_overrides = json.loads(
        apply_placeholders(context, context.text)
    )
    app.client = app.create_client_instance(config_overrides)


@then('we store response in "{tag}"')
def step_impl_store_response_in_cts(context, tag):
    data = json.loads(context.response.content)
    setattr(context, tag, data)
