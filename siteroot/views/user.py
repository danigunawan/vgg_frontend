from django.conf import settings
from django.shortcuts import render_to_response, redirect
from django.http import HttpResponseBadRequest, Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from django.views.decorators.cache import cache_page
from django.contrib.auth.views import login as auth_views_login
from django.contrib.auth.views import logout as auth_views_logout

import json
import sys
import os
import urllib.parse
from PIL import Image
import copy
import requests
import time
import re

# add 'controllers' to the path so that we can import stuff from it
sys.path.append(os.path.join(settings.BASE_DIR, 'siteroot', 'controllers'))

# imports from the controller
from retengine.engine import backend_client
from retengine import query_translations
from retengine.models import opts

class UserPages:
    """
        This class provides rendering services for the pages that can be accessed by a regular user
        Members:
            visor_controller: an instance of the visor backend interface controller
    """

    def __init__(self, visor_controller):
        """
            Initializes an instance of this class
            Arguments:
                visor_controller: an instance of the visor backend interface controller
        """
        self.visor_controller = visor_controller


    def login(self, request):
        """ Customized login page to be able to add extra content """
        home_location = settings.SITE_PREFIX + '/'
        if 'HTTP_X_FORWARDED_HOST' in request.META:
            home_location = 'http://' + request.META['HTTP_X_FORWARDED_HOST'] + home_location
        next_page = request.GET.get('next', None)
        context = {
        'NEXT': next_page,
        'SITE_PREFIX': settings.SITE_PREFIX,
        'HOME_LOCATION': home_location,
        }
        return auth_views_login(request, template_name='login.html', extra_context=context)


    def logout(self, request):
        """ Customized logout page to be able to specify the next page after login out """
        next_page = settings.SITE_PREFIX + '/'
        if 'HTTP_X_FORWARDED_HOST' in request.META:
            next_page = 'http://' + request.META['HTTP_X_FORWARDED_HOST'] + next_page
        return auth_views_logout(request, next_page=next_page)


    @method_decorator(require_GET)
    def user_profile(self, request):
        """
            Landing page after logging in.
            TODO: Implement user profile page. Temporarily redirecting to the admintools page, because admin is the only user.
            Arguments:
               request: request object only used to check that it is a GET.
            Returns:
               redirect to the admintools page
        """
        return redirect('admintools')


    @method_decorator(require_GET)
    def nobackend(self, request, template='nobackend.html'):
        """
            Renders a page indicating that no backend has been detected.
            The page checks the presence of the backend every 5 seconds.
            Arguments:
               request: request object only used to check that it is a GET.
            Returns:
               HTTP 200 if the page is successfully rendered
        """
        # compute home location taking into account any possible redirections
        home_location = settings.SITE_PREFIX + '/'
        if 'HTTP_X_FORWARDED_HOST' in request.META:
            home_location = 'http://' + request.META['HTTP_X_FORWARDED_HOST'] + home_location

        # set up rendering context and render the page
        context = {
        'SITE_TITLE': settings.VISOR['title'],
        'HOME_LOCATION' : home_location,
        'AUTHENTICATED' : request.user.is_authenticated()
        }
        return render_to_response(template, context)


    @method_decorator(ensure_csrf_cookie)
    @method_decorator(require_GET)
    def site_index(self, request, template='index.html'):
        """
            Homepage - provides entry point into search
            Only GET requests are allowed. This method is CSRF protected
            to protect the POST triggered when uploading an image for searching.
            Arguments:
               request: request object containing details of the user session
            Returns:
               HTTP 200 if the page is successfully rendered
        """
        # Check if there is a session already created. Create one if necessary.
        if request.session.session_key == None:
            print ('Creating user session ...')
            request.session.create()

        # check if the backend is reachable or not
        if self.visor_controller.opts.check_backends_reachable and self.visor_controller.is_backend_reachable() == "0":
            return redirect('nobackend')

        # get engines info, for including it in the page
        available_engines = self.visor_controller.opts.engines_dict

        # check if the selected 'engine' has been specified and whether it is valid or not
        engine = request.GET.get('engine', None)
        if engine not in available_engines.keys():
            # use the first engine by default
            engine = list(self.visor_controller.opts.engines_dict)[0]

        # compute home location taking into account any possible redirections
        home_location = settings.SITE_PREFIX + '/'
        if 'HTTP_X_FORWARDED_HOST' in request.META:
            home_location = 'http://' + request.META['HTTP_X_FORWARDED_HOST'] + home_location

        # check which engines support image input
        str_engines_with_image_input_support = ''
        for key in available_engines.keys():
            if self.visor_controller.opts.engines_dict[key]['imgtools_postproc_module'] != None:
                if len(str_engines_with_image_input_support) > 0:
                    str_engines_with_image_input_support = str_engines_with_image_input_support + ' '
                str_engines_with_image_input_support = str_engines_with_image_input_support + key

        # check if the 'Getting Started' tour should be activated
        VISOR_SETTINGS = settings.VISOR
        enable_tour = self.visor_controller.opts.enable_tour
        tour = request.GET.get('tour', 0)
        open_tour = (int(tour) != 0) and enable_tour

        # word cloud stuff for the 'text' engine
        words_json = None
        if 'text' in available_engines.keys():
            try:
                dataset = list(VISOR_SETTINGS['datasets'].keys())[0]
                f = open(available_engines['text']['word_frecuency_path'], 'r')
                words_json = json.load(f)
                f.close()
                words = []
                for item in words_json:
                    words.append( {
                    'text': item['text'],
                    'weight' : item['weight'],
                    'link': home_location + 'searchproc_qstr?q=%s&qtype=text&dsetname=%s&engine=text' % ( item['text'].lower(), dataset)
                    } )
                words_json = json.dumps(words)
            except Exception as e:
                print ('WARNING: Could not load word frequency for word cloud. Exception ', e)
                # In case of any exception, just disable the world cloud and move on
                words_json=None
                pass

        # set up rendering context and render the page
        context = {
        'AUTHENTICATED' : request.user.is_authenticated(),
        'AVAILABLE_ENGINES': available_engines,
        'DATASETS': VISOR_SETTINGS['datasets'],
        'SITE_TITLE': VISOR_SETTINGS['title'],
        'DISABLE_AUTOCOMPLETE': VISOR_SETTINGS['disable_autocomplete'],
        'ENABLE_TOUR' : enable_tour,
        'OPEN_TOUR' : open_tour,
        'ENGINES_WITH_IMAGE_SEARCH_SUPPORT': str_engines_with_image_input_support,
        'WORD_CLOUD_WORDS': words_json
        }
        return render_to_response(template, context)


    @method_decorator(require_GET)
    def waitforit_process(self, request, template='waitforit.html'):
        """
            Page that is displayed when two concurrent threads are executing the same query.
            One of the threads must wait for the results of the other. Hence it has to
            wait until the results are obtained.
            Only GET requests are allowed.
            Arguments:
               request: request object containing details of the user session
            Returns:
               HTTP 200 if the page is successfully rendered
        """

        # compute home location taking into account any possible redirections
        home_location = settings.SITE_PREFIX + '/'
        if 'HTTP_X_FORWARDED_HOST' in request.META:
            home_location = 'http://' + request.META['HTTP_X_FORWARDED_HOST'] + home_location

        # get parameters needed for the redirection to the search_process (inside the template)
        engine = request.GET.get('engine', None)
        query_string = request.GET.get('q', None)
        query_type = request.GET.get('qtype', '')
        dataset_name = request.GET.get('dsetname', None)

        if query_string:
            query_string = query_string.replace('#', '%23') #  html-encode curated search character

        # render with context
        context = {
        'HOME_LOCATION': home_location,
        'QUERY_STRING': query_string,
        'QUERY_TYPE': query_type,
        'ENGINE': engine,
        'DATASET_NAME': dataset_name,
        }
        return render_to_response(template, context)


    @method_decorator(require_GET)
    def search_process(self, request, template='searchproc.html'):
        """
            Starts the search process and starts rendering the web page with the results.
            Redirects the search to other methods, if needed
            Only GET requests are allowed.
            Arguments:
               request: request object containing details of the user session
               and the parameters for the search
            Returns:
               HTTP 200 if the page is successfully rendered
        """
        VISOR_SETTINGS = settings.VISOR
        engine = request.GET.get('engine', None)
        query_string = request.GET.get('q', None)
        query_type = request.GET.get('qtype', '')
        dataset_name = request.GET.get('dsetname', None)
        prev_qsid = request.GET.get('prev_qsid', None)

        # compute home location taking into account any possible redirections
        home_location = settings.SITE_PREFIX + '/'
        if 'HTTP_X_FORWARDED_HOST' in request.META:
            home_location = 'http://' + request.META['HTTP_X_FORWARDED_HOST'] + home_location

        if not query_string:
            if not engine:
                return redirect(home_location)
            else:
                return redirect(home_location + '?engine=' + engine)

        # Only accept text queries with acceptable characters
        if ((query_type == opts.Qtypes.text) and
            (query_string != 'keywords:%s' % settings.KEYWORDS_WILDCARD) and
            (not re.match("^[#$]?[a-zA-Z0-9_\-\ +,:;.!\?()\[\]]*$", query_string))):
            message = 'Your text query contains invalid characters. Please use only letters, numbers, spaces or common word dividers. Also avoid using the keyword-wildcard (%s) along other keywords.' % settings.KEYWORDS_WILDCARD
            redirect_to = settings.SITE_PREFIX
            return render_to_response("alert_and_redirect.html", context={'REDIRECT_TO': redirect_to, 'MESSAGE': message})

        available_engines = self.visor_controller.opts.engines_dict
        if engine in available_engines.keys(): # if engine is 'None' or invalid, the user should get an error

            # In case of an image query, check if the engine support images as input.
            # Although in general this kind of query should not reach this point.
            engine_has_img_postproc_module = self.visor_controller.opts.engines_dict[engine].get('imgtools_postproc_module', None) != None
            if query_type == opts.Qtypes.image and not engine_has_img_postproc_module:
                message = 'The selected engine does not support image queries. Please correct your search or select a different engine.'
                redirect_to = settings.SITE_PREFIX
                return render_to_response("alert_and_redirect.html", context={'REDIRECT_TO': redirect_to, 'MESSAGE': message})

            # In case of a (non-curated) text query, with the image postprocessing module set to 'download_disabled',
            # try to transform the text query into a keyword query. If it is not possible, report an error.
            img_postproc_module_is_download_disabled = self.visor_controller.opts.engines_dict[engine].get('imgtools_postproc_module', None) == 'download_disabled'
            if (query_type == opts.Qtypes.text and img_postproc_module_is_download_disabled and
                not query_string.startswith('keywords:') and query_string[0] != '#' and query_string[0] != '$' ):
                new_query_string = None
                try:
                    keyword_list = self.visor_controller.metadata_handler.get_search_suggestions(query_string)
                    if settings.KEYWORDS_WILDCARD in keyword_list: # remove the wildcard, to avoid returning everything
                        keyword_list.remove(settings.KEYWORDS_WILDCARD)
                    new_query_string = 'keywords:'
                    for idx in range(len(keyword_list)):
                        if idx > 0:
                            new_query_string = new_query_string + ','
                        new_query_string = new_query_string + keyword_list[idx]
                except Exception as e:
                    print (e)
                    new_query_string = None
                    pass
                if new_query_string is None or new_query_string=='keywords:':
                    message = 'Your text query does not match any keyword in the dataset. Please input an image or use the keyword-selection button to find a valid keyword.'
                    redirect_to = settings.SITE_PREFIX
                    return render_to_response("alert_and_redirect.html", context={'REDIRECT_TO': redirect_to, 'MESSAGE': message})
                else:
                    try:
                        new_query_string = urllib.parse.quote(new_query_string)
                        return redirect(settings.SITE_PREFIX + '/searchproc_qstr?q=%s&qtype=%s&dsetname=%s&engine=%s' % (new_query_string, query_type, dataset_name, engine))
                    except Exception as e:
                        print (e)
                        pass

            # save main details in session
            request.session['query_string'] = query_string
            request.session['query_type'] = query_type
            request.session['dataset_name'] = dataset_name
            request.session['engine'] = engine

            # generate session and query id
            query = query_translations.querystr_tuple_to_query(query_string, query_type, dataset_name, engine, prev_qsid)
            query_ses_info = {}
            query_ses_info['query_ses_id'] = self.visor_controller.query_key_cache.gen_query_session_id(query)

            #NOTE: The two previous instructions can be replaced by the instruction below
            #      to start the query immediately, but then it takes longer to switch to the searchproc page
            #query_ses_info = self.visor_controller.create_query_session(query, request.session.session_key)

            # check whether the query is cached...
            try:
                # but use a lock to guarantee this thread's exclusive access
                self.visor_controller.query_available_lock.acquire()
                # check if query in cache

                query_ses_info['cached'] = self.visor_controller.check_query_in_cache_no_locking(query, request.session.session_key)
                if not query_ses_info['cached']:
                    # if it is not cached, check the status of the query, in case another thread is running it
                    status = self.visor_controller.interface.query_manager.get_query_status_from_definition(query)
                    if status != None and status.state < opts.States.results_ready:
                        # if another thread is running it and it is not done, redirect to the 'wait for it' page,
                        # which will automatically redirect to this page to retry the search
                        if query_string[0] == '#':
                            query_string = query_string.replace('#', '%23') #  html-encode curated search character
                            query_type = opts.Qtypes.text # every curated query is a text query
                        return redirect(settings.SITE_PREFIX + '/waitforit?q=%s&qtype=%s&dsetname=%s&engine=%s' % (query_string, query_type, dataset_name, engine))
            finally:
                # release access
                self.visor_controller.query_available_lock.release()

            if query_ses_info['cached']:
                # if cached then redirect to searchres immediately with the query_ses_id
                return redirect(settings.SITE_PREFIX + '/searchres?qsid='+ query_ses_info['query_ses_id'])
            else:
                skip_query_progress = self.visor_controller.opts.engines_dict[engine].get('skip_query_progress', False)
                if skip_query_progress or (
                    engine == 'instances' and query_type == 'dsetimage'  # For this specific case, we can also skip the query progress
                                                                         # because results are instant ....
                   ) or query_string.startswith('keywords:'):            # .... and the same applies to this other case

                    # NOTE: The code in this if-statement replaces the process implemented in 'searchproc.html', which
                    # performs the query with a visual feedback and downloading images. In cases when the backend does
                    # not need images as input, and the results are obtained almost instantly, you can use this code to
                    # skip the visual feedback and go directly to the results page. In any other case it is recommended
                    # to let the code in 'searchproc.html' run.
                    try:
                        search_finished = False
                        seconds_between_requests = 0.25 # Adjust to your needs, but if results are almost instant this should be ok.
                        if 'HTTP_X_FORWARDED_HOST' not in request.META:
                            host = request.META['HTTP_HOST']
                            if host.startswith('127.0.0.1') or host.startswith('localhost') and (
                               'SERVER_PORT' in request.META and request.META['SERVER_PORT'] not in host):
                                host = host.split(':')[0]
                                host = host + ':' + request.META['SERVER_PORT']
                            home_location = 'http://' + host + home_location
                        else:
                            if 'SERVER_PORT' in request.META:
                                home_location = 'http://127.0.0.1:' + request.META['SERVER_PORT'] + settings.SITE_PREFIX + '/'
                            else:
                                home_location = 'http://127.0.0.1:8000' + settings.SITE_PREFIX + '/'

                        while not search_finished:
                            # Start query or get query status
                            result = requests.get(home_location + 'execquery?qsid=' + query_ses_info['query_ses_id'])
                            response = result.json()
                            # Check response
                            if response['state'] >= opts.States.fatal_error_or_socket_timeout:
                                # if something went wrong, get brutally out of the try
                                raise Exception(response['err_msg'])
                            if response['state'] < opts.States.results_ready:
                                # if not ready, sleep a bit
                                time.sleep(seconds_between_requests)
                            else:
                                # otherwise, get out of the try normally
                                search_finished = True
                    except Exception as e:
                        # display error message and go back home
                        redirect_to = settings.SITE_PREFIX
                        msg = str(e)
                        msg = msg.replace('\'', '')
                        return render_to_response("alert_and_redirect.html", context={'REDIRECT_TO': redirect_to, 'MESSAGE': msg})

                    # if we actually manage to reach this point, display search results
                    return redirect(settings.SITE_PREFIX + '/searchres?qsid='+ query_ses_info['query_ses_id'])
                else:
                    # otherwise we need to process query normally
                    # render processing template to start a query and monitor its progress
                    context = {
                    'HOME_LOCATION': home_location,
                    'SITE_TITLE': VISOR_SETTINGS['title'],
                    'ENGINE': engine,
                    'AVAILABLE_ENGINES': available_engines,
                    'DATASETS': VISOR_SETTINGS['datasets'],
                    'QUERY_STRING': query_string,
                    'QUERY_TYPE': query_type,
                    'DATASET_NAME': dataset_name,
                    'QUERY_ID' : query_ses_info['query_ses_id'],
                    'CURATED': query_string[0] == '#'
                    }
                    return render_to_response(template, context)

        raise Http404("Could not start query. Possibly the search engine does not exist.")


    @method_decorator(ensure_csrf_cookie)
    @method_decorator(require_GET)
    def searchres(self, request, template='searchres.html'):
        """
            Renders the search results. Redirects to the home page if the query has expired.
            Only GET requests are allowed. This method is CSRF protected to protect the POST triggered
            when changing view modes and when uploading images for searching.
            Arguments:
               request: request object containing details of the user session
               and the parameters for the search
            Returns:
               HTTP 200 if the page is successfully rendered. HTTP 404 if the query id is missing.
        """
        query_id = request.GET.get('qsid', None)
        if query_id == None:
            raise Http404("Query ID not specified. Query does not exist")

        # get query definition dict from query_ses_id
        query = self.visor_controller.query_key_cache.get_query_details(query_id)

        # check that the query is still valid (not expired)
        if query == None or ('engine' not in request.session):
            message = 'This query has expired. Please enter your query again in the home page.'
            redirect_to = settings.SITE_PREFIX
            return render_to_response("alert_and_redirect.html", context={'REDIRECT_TO': redirect_to, 'MESSAGE': message})

        # get other parameters
        page = request.GET.get('page', 1)
        engine = request.GET.get('engine', None)
        view = request.GET.get('view', None)
        page = int(page)

        # get default view if no view specified
        if not view:
            try:
                if request.session.get('viewmode'):
                    view = request.session.get('viewmode')
                else:
                    view = self.visor_controller.opts.default_view
            except:
                view = self.visor_controller.opts.default_view
            finally:
                request.session['viewmode'] = view # store this value in the user session

        # get query result
        query_data = self.visor_controller.get_query_result(query, request.session.session_key, query_ses_id=query_id)

        # if there is no query_data, ...
        if not query_data.rlist:
            # ... if the query is done, then it must have returned no results. Show message and redirect to home page
            if query_data.status.state == opts.States.results_ready:
                message = 'This query did not return any results. Please enter a diferent query in the home page.'
                redirect_to = settings.SITE_PREFIX
                return render_to_response("alert_and_redirect.html", context={'REDIRECT_TO': redirect_to, 'MESSAGE': message})
            else:  # ... otherwise redirect to searchproc_qstr to continue the query
                (qtext, qtype, dsetname, engine) = query_translations.query_to_querystr_tuple(query)
                if qtext[0] == '#':
                    qtext = qtext.replace('#', '%23') #  html-encode curated search character
                    qtype = opts.Qtypes.text # every curated query is a text query
                return redirect(settings.SITE_PREFIX + '/searchproc_qstr?q=%s&qtype=%s&dsetname=%s&engine=%s' % (qtext, qtype, dsetname, engine))

        # compute home location taking into account any possible redirections
        home_location = settings.SITE_PREFIX + '/'
        if 'HTTP_X_FORWARDED_HOST' in request.META:
            home_location = 'http://' + request.META['HTTP_X_FORWARDED_HOST'] + home_location

        # extract query string, specially needed when the query type is not 'text'
        query_string = query_translations.query_to_querystr(query)

        # get engines info, for including it in the page
        available_engines = self.visor_controller.opts.engines_dict

        # check which engines support image input
        str_engines_with_image_input_support = ''
        for key in available_engines.keys():
            if self.visor_controller.opts.engines_dict[key]['imgtools_postproc_module'] != None:
                if len(str_engines_with_image_input_support) > 0:
                    str_engines_with_image_input_support = str_engines_with_image_input_support + ' '
                str_engines_with_image_input_support = str_engines_with_image_input_support + key

        # set up rendering context and render the page
        VISOR_SETTINGS = settings.VISOR
        context = {
        'AUTHENTICATED' : request.user.is_authenticated(),
        'HOME_LOCATION': home_location,
        'SITE_TITLE': VISOR_SETTINGS['title'],
        'QUERY_ID': query_id,
        'QUERY_STRING' : query_string,
        'QUERY': query,
        'PAGE': page,
        'ENGINE' : request.session['engine'],
        'AVAILABLE_ENGINES': available_engines,
        'DATASETS': VISOR_SETTINGS['datasets'],
        'PROCESSING_TIME' : '%.2f' % query_data.status.exectime_processing,
        'TRAINING_TIME' : '%.2f' % query_data.status.exectime_training,
        'RANKING_TIME' : '%.2f' % query_data.status.exectime_ranking,
        'DISABLE_AUTOCOMPLETE': VISOR_SETTINGS['disable_autocomplete'],
        'ENGINES_WITH_IMAGE_SEARCH_SUPPORT': str_engines_with_image_input_support,
        'VIEWMODE': view,
        'VIEWSEL': self.visor_controller.opts.enable_viewsel and not query_string.startswith('keywords:')
        }
        return render_to_response(template, context)


    @method_decorator(cache_page(60 * 30)) # view will be cached for 30 minutes
    @method_decorator(require_GET)
    def searchresroislist(self, request):
        """
            Renders the list of results in roi view mode.
            Only GET requests are allowed.
            It reuses the code for the standard list in grid view mode, but
            requesting to show roi-only images.
            Arguments:
               request: request object containing details of the user session
               and the parameters for the search
            Returns:
               HTTP 200 if the page is successfully rendered.
        """

        return self.searchreslist(request, template='searchresroislist.html', rois=True)


    @method_decorator(cache_page(60 * 30)) # view will be cached for 30 minutes
    @method_decorator(require_GET)
    def searchreslist(self, request, template='searchreslist.html', rois=False):
        """
            Renders the list of results in grid mode.
            Only GET requests are allowed.
            Arguments:
               request: request object containing details of the user session
               and the parameters for the search
            Returns:
               HTTP 200 if the page is successfully rendered.
        """
        query_id = request.GET.get('qsid', None)
        if query_id == None:
            raise Http404("Query ID not specified. Query does not exist")

        # get query definition dict from query_ses_id
        query = self.visor_controller.query_key_cache.get_query_details(query_id)

        # check that the query is still valid (not expired)
        if query == None or ('engine' not in request.session):
            message = 'This query has expired. Please enter your query again in the home page.'
            redirect_to = settings.SITE_PREFIX
            return render_to_response("alert_and_redirect.html", context={'REDIRECT_TO': redirect_to, 'MESSAGE': message})

        page = request.GET.get('page', 1)
        processingtime = request.GET.get('processingtime', '0.0')
        trainingtime = request.GET.get('trainingtime', '0.0')
        rankingtime = request.GET.get('rankingtime', '0.0')
        #genres = request.GET.get('genres', None) # not used at the moment

        if page == '':
            page = '1'
        if processingtime == '':
            processingtime = '0.0'
        if trainingtime == '':
            trainingtime = '0.0'
        if rankingtime == '':
            rankingtime = '0.0'

        page = int(page)
        processingtime = float(processingtime)
        trainingtime = float(trainingtime)
        rankingtime = float(rankingtime)

        # get current engine from session
        engine = request.session['engine']

        # get query result
        query_data = self.visor_controller.get_query_result(query, request.session.session_key, query_ses_id=query_id)

        # For the instances engine, if the query included a ROI, remove results without ROI
        query_string = query_translations.query_to_querystr(query)
        if 'roi' in query_string and engine == 'instances':
            rlist = []
            for ritem in query_data.rlist:
                if 'roi' in ritem:
                    rlist.append(ritem)
        else:
            rlist = query_data.rlist

        # if there is no query_data, ...
        if not rlist:
            # ... if the query is done, then it must have returned no results. Show message and redirect to home page
            if query_data.status.state == opts.States.results_ready:
                message = 'This query did not return any results. Please enter a diferent query in the home page.'
                redirect_to = settings.SITE_PREFIX
                return render_to_response("alert_and_redirect.html", context={'REDIRECT_TO': redirect_to, 'MESSAGE': message})
            else:  # ... otherwise redirect to searchproc_qstr to continue the query
                (qtext, qtype, dsetname, engine) = query_translations.query_to_querystr_tuple(query)
                if qtext[0] == '#':
                    qtext = qtext.replace('#', '%23') #  html-encode curated search character
                    qtype = opts.Qtypes.text # every curated query is a text query
                return redirect(settings.SITE_PREFIX + '/searchproc_qstr?q=%s&qtype=%s&dsetname=%s&engine=%s' % (qtext, qtype, dsetname, engine))

        # Get the image count here, but watch out for modifications afterwards.
        # When the image_count == None some information won't be displayed in the results page.
        image_count = len(rlist)

        # Check we don't have JUST one result with an empty list
        if image_count==1 and len(rlist[0]['path'])==0:
            message = 'This query did not return any results. Please enter a diferent query in the home page.'
            redirect_to = settings.SITE_PREFIX
            return render_to_response("alert_and_redirect.html", context={'REDIRECT_TO': redirect_to, 'MESSAGE': message})

        # extract pages
        (rlist, page_count) = self.visor_controller.page_manager.get_page(rlist, page)
        pages = self.visor_controller.page_manager.construct_page_array(page, page_count)
        if page > page_count:
            page = page_count

        # set paths of image thumbnails
        sa_thumbs = 'thumbnails/%s/' % query['dsetname']
        if rois:
            sa_thumbs = 'regions/%s/' % query['dsetname']

        # prepare the details of every item in the list, for rendering the page
        for ritem in rlist:
            # Add the metadata of each item. This could be programme name etc., otherwise defaults to filename
            try:
                ritem['desc'] = self.visor_controller.metadata_handler.get_desc_from_fname(ritem['path'], query['dsetname'])
            except Exception:
                (fpath, fname) = os.path.split(ritem['path'])
                ritem['desc'] = fname
            # add extra tags if necessary
            dsetresid = ritem['path']
            if 'uri' in ritem:
                dsetresid = dsetresid+ ',uri:%s' % ritem['uri']
            ritem['dsetresid'] = dsetresid
            if 'score' not in ritem:
                ritem['score'] = 0

            if 'roi' in ritem:
                thumbnailroi = ',roi:' + ritem['roi']
                ritem['thumbnailroi'] = thumbnailroi
            elif rois and self.visor_controller.opts.engines_dict[engine]['backend_port']:
                # If the ROI was not specified, do a final attempt to retrieve it
                # from the backend
                query = self.visor_controller.query_key_cache.get_query_details(query_id)
                backend_port = self.visor_controller.opts.engines_dict[engine]['backend_port']
                ses = backend_client.Session(backend_port)
                func_in = {}
                func_in['func'] = 'getRoi'
                func_in['frame_path'] = ritem['path']
                func_in['query_string'] = query['qdef']
                roi_request = json.dumps(func_in)
                roi_response = ses.custom_request(roi_request)
                json_response = json.loads(roi_response)
                if 'roi' in json_response and len(json_response['roi']) > 0:
                    roi = json_response['roi']
                    if isinstance(roi, list):
                        roi = '_'.join(roi[:10]) # string roi should be x1_y1_x2_y1_x2_y2_x1_y2_x1_y1
                    ritem['thumbnailroi'] = ',roi:' + roi

        # compute home location taking into account any possible redirections
        home_location = settings.SITE_PREFIX + '/'
        if 'HTTP_X_FORWARDED_HOST' in request.META:
            home_location = 'http://' + request.META['HTTP_X_FORWARDED_HOST'] + home_location

        similar_search_engine = None
        VISOR_SETTINGS = settings.VISOR
        if 'engine_for_similar_search' in VISOR_SETTINGS['engines'][engine]:
            similar_search_engine = VISOR_SETTINGS['engines'][engine]['engine_for_similar_search']

        # set up rendering context and render the page
        VISOR_SETTINGS = settings.VISOR
        context = {
        'HOME_LOCATION': home_location,
        'QUERY_ID': query_id,
        'QUERY': query,
        'RDATA': rlist,
        'IMAGE_COUNT' : image_count,
        'PAGE_COUNT' : page_count,
        'PAGE': page,
        'SA_THUMBS' : sa_thumbs,
        'PAGES': pages,
        'PROCESSING_TIME' : processingtime,
        'TRAINING_TIME' : trainingtime,
        'RANKING_TIME' : rankingtime,
        'ENGINE': engine,
        'SIMILAR_ENGINE': similar_search_engine,
        'ENGINE_CAN_SAVE_UBER' : self.visor_controller.opts.engines_dict[engine]['can_save_uber_classifier'] and not query_string.startswith('keywords:'),
        'ENGINE_HAS_IMG_POSTPROC_MODULE' : self.visor_controller.opts.engines_dict[engine]['imgtools_postproc_module'] != None and not query_string.startswith('keywords:'),
        }
        return render_to_response(template, context)


    @method_decorator(require_GET)
    def get_trainingimages(self, request, template='trainingimages.html'):
        """
            Renders the training image summary page
            Only GET requests are allowed.
            Arguments:
               request: request object containing details of the user session
               and the parameters for the search
            Returns:
               HTTP 200 if the page is successfully rendered. HTTP 404 if the query id is missing.
        """
        query_id = request.GET.get('qsid', None)
        if query_id == None:
            raise Http404("Query ID not specified. Query does not exist")

        # get query definition dict from query_ses_id
        query = self.visor_controller.query_key_cache.get_query_details(query_id)

        # check that the query is still valid (not expired)
        if query == None:
            message = 'This query has expired. Please enter your query again in the home page.'
            redirect_to = settings.SITE_PREFIX
            return render_to_response("alert_and_redirect.html", context={'REDIRECT_TO': redirect_to, 'MESSAGE': message})

        viewmode = request.GET.get('view', None)
        page = request.GET.get('page', None)
        if page:
            page = int(page)

        # get list of training images for the query
        trainimgs = self.visor_controller.interface.get_training_images(query, user_ses_id=request.session.session_key)

        # dsetname and page variables used to allow the user to return
        # to calling results page
        if query['qtype'] == opts.Qtypes.dsetimage:
            sa_thumbs = 'thumbnails/%s/' % query['dsetname']
        elif query['qtype'] == opts.Qtypes.refine:
            sa_thumbs = 'postrainimgs/'
        elif query['qtype'] == opts.Qtypes.text:
            sa_thumbs = 'postrainimgs/'
        elif query['qtype'] == opts.Qtypes.image:
            sa_thumbs = 'uploadedimgs/'

        # No matter the query type, check if it is a curated query
        if query['qdef'][0] == '#':
            sa_thumbs = 'curatedtrainimgs/'

        # compute home location taking into account any possible redirections
        home_location = settings.SITE_PREFIX + '/'
        if 'HTTP_X_FORWARDED_HOST' in request.META:
            home_location = 'http://' + request.META['HTTP_X_FORWARDED_HOST'] + home_location

        # prepare the details of every image in the list, for rendering the page
        if trainimgs:
            for image in trainimgs:
                image_path = image['image']
                anno = str(image['anno'])
                if anno == '1' or anno == '+1':
                    anno_style = 'roi_box_positive'
                    anno = '1'
                elif anno == '-1':
                    anno_style = 'roi_box_negative'
                else:
                    anno_style = 'roi_box_skip'
                image['anno'] = anno
                image['anno_style'] = anno_style

                # if case of these two types of search, be sure to add the
                # thumbs suffix, so that a thumbnail image is correctly downloaded
                # if a search is launched from this page
                image_path = image_path.replace('#', '%23') #  html-encode curated search character
                if  (query['qtype'] == opts.Qtypes.refine or
                     query['qtype'] == opts.Qtypes.text):
                    img_id = sa_thumbs + image_path
                else:
                    img_id = image_path

                if 'roi' in image:
                    img_id = img_id + ',roi:'
                    idx = 0
                    roi = image['roi']
                    for coord in roi:
                        if idx == 0:
                            img_id = img_id + '%0.2f' % (coord)
                        else:
                            img_id = img_id + '_%0.2f' % (coord)
                        idx = idx + 1
                image['img_id'] = img_id
                image['image'] = urllib.parse.quote(image['image'])


        # set up rendering context and render the page
        context = {
        'QUERY_ID': query_id,
        'DATASET_NAME': query['dsetname'],
        'QUERY_TYPE': query['qtype'],
        'TRAINIMGS' : trainimgs,
        'PAGE': page,
        'SA_THUMBS' : sa_thumbs,
        'ENGINE': request.session['engine']
        }
        return render_to_response(template, context)


    @method_decorator(require_GET)
    def selectpageimages(self, request, template='selectpageimages.html'):
        """
            Renders an image result page and allows the user to select each image.
            Only GET requests are allowed.
            Arguments:
               request: request object containing details of the user session, the query id and the page to be rendered
            Returns:
               HTTP 200 if the page is successfully rendered. HTTP 404 if the query id is missing.
        """
        query_id = request.GET.get('qsid', None)
        if query_id == None:
            raise Http404("Query ID not specified. Query does not exist")

        # get query definition dict from query_ses_id
        query = self.visor_controller.query_key_cache.get_query_details(query_id)

        # check that the query is still valid (not expired)
        if query == None:
            message = 'This query has expired. Please enter your query again in the home page.'
            redirect_to = settings.SITE_PREFIX
            return render_to_response("alert_and_redirect.html", context={'REDIRECT_TO': redirect_to, 'MESSAGE': message})

        viewmode = request.GET.get('view', None)
        page = request.GET.get('page', 1)
        if page:
            page = int(page)

        # get current engine from session
        engine = request.session['engine']

        # get query result
        query_data = self.visor_controller.get_query_result(query, request.session.session_key, query_ses_id=query_id)

        # For the instances engine, if the query included a ROI, remove results without ROI
        query_string = query_translations.query_to_querystr(query)
        if 'roi' in query_string and engine == 'instances':
            rlist = []
            for ritem in query_data.rlist:
                if 'roi' in ritem:
                    rlist.append(ritem)
        else:
            rlist = query_data.rlist

        # if there is no query_data, ...
        if not rlist:
            # ... if the query is done, then it must have returned no results. Show message and redirect to home page
            if query_data.status.state == opts.States.results_ready:
                message = 'This query did not return any results. Please enter a diferent query in the home page.'
                redirect_to = settings.SITE_PREFIX
                return render_to_response("alert_and_redirect.html", context={'REDIRECT_TO': redirect_to, 'MESSAGE': message})
            else:  # ... otherwise redirect to searchproc_qstr to continue the query
                (qtext, qtype, dsetname, engine) = query_translations.query_to_querystr_tuple(query)
                if qtext[0] == '#':
                    qtext = qtext.replace('#', '%23') #  html-encode curated search character
                    qtype = opts.Qtypes.text # every curated query is a text query
                return redirect(settings.SITE_PREFIX + '/searchproc_qstr?q=%s&qtype=%s&dsetname=%s&engine=%s' % (qtext, qtype, dsetname, engine))

        # extract pages
        (rlist, page_count) = self.visor_controller.page_manager.get_page(rlist, page)
        pages = self.visor_controller.page_manager.construct_page_array(page, page_count)
        if page > page_count:
            page = page_count

        # set paths of image thumbnails
        sa_thumbs = 'thumbnails/%s/' % query['dsetname']

        # compute home location taking into account any possible redirections
        home_location = settings.SITE_PREFIX + '/'
        if 'HTTP_X_FORWARDED_HOST' in request.META:
            home_location = 'http://' + request.META['HTTP_X_FORWARDED_HOST'] + home_location

        # prepare the details of every item in the list, for rendering the page
        for ritem in rlist:
            ritem['anno'] = '1'
            ritem['anno_style'] = 'roi_box_positive'

        # set up rendering context and render the page
        context = {
        'QUERY_ID': query_id,
        'DATASET_NAME': query['dsetname'],
        'QUERY_TYPE': query['qtype'],
        'IMAGE_LIST' : rlist,
        'PAGE': page,
        'SA_THUMBS' : sa_thumbs,
        'ENGINE': request.session['engine']
        }
        return render_to_response(template, context)


    @method_decorator(require_GET)
    def viewdetails(self, request, template='details.html'):
        """
            Renders the detailed page of a specific image.
            Only GET requests are allowed.
            Arguments:
               request: request object containing details of the user session
               and the parameters for the search
            Returns:
               HTTP 200 if the page is successfully rendered. HTTP 404 if the query id is missing.
               HTTP 400 if the dataset is not specified
        """
        query_id = request.GET.get('qsid', None)
        if query_id == None:
            raise Http404("Query ID not specified. Query does not exist")

        # check that the query is still valid (not expired)
        if 'engine' not in request.session:
            message = 'This query has expired. Please enter your query again in the home page.'
            redirect_to = settings.SITE_PREFIX
            return render_to_response("alert_and_redirect.html", context={'REDIRECT_TO': redirect_to, 'MESSAGE': message})

        page = request.GET.get('page', 1)
        viewmode = request.GET.get('view', None)
        dsetname = request.GET.get('dsetname', None)
        dsetresid = request.GET.get('dsetresid', None)
        roi = request.GET.get('roi', None)

        # check dataset is specified
        if not dsetname or not dsetresid:
            return HttpResponseBadRequest('Missing dataset ID')

        # compute home location taking into account any possible redirections
        home_location = settings.SITE_PREFIX + '/'
        if 'HTTP_X_FORWARDED_HOST' in request.META:
            home_location = 'http://' + request.META['HTTP_X_FORWARDED_HOST'] + home_location

        # get engines info, for including it in the page
        available_engines = copy.deepcopy(self.visor_controller.opts.engines_dict)
        for engine in available_engines:
            if available_engines[engine]['url'] == '/':
                available_engines[engine]['url'] = home_location

        # For now, we cannot trigger a search with the 'text' engine
        # from the image details page
        if 'text' in available_engines.keys():
            del available_engines['text']

        # if there is no more than one engine, there is no point on passing
        # this info to the renderer
        if len(available_engines.keys()) == 1:
            available_engines = None

        # get image name
        imagename = dsetresid.split(',')[0]
        imloc = dsetname + '/' + imagename

        # read the image
        image = Image.open(os.path.join(settings.PATHS['datasets'], imloc))
        (imwidth, imheight) = image.size
        imformat = image.format

        engine = request.session['engine']
        if not roi and self.visor_controller.opts.engines_dict[engine]['backend_port']:
            # If the ROI was not specified, do a final attempt to retrieve it
            # from the backend
            query = self.visor_controller.query_key_cache.get_query_details(query_id)
            if query:
                backend_port = self.visor_controller.opts.engines_dict[engine]['backend_port']
                ses = backend_client.Session(backend_port)
                func_in = {}
                func_in['func'] = 'getRoi'
                func_in['frame_path'] = imagename
                func_in['query_string'] = query['qdef']
                request = json.dumps(func_in)
                response = ses.custom_request(request)
                json_response = json.loads(response)
                if 'roi' in json_response and  len(json_response['roi']) > 0:
                    roi = json_response['roi']

        all_rois = None
        if self.visor_controller.opts.engines_dict[engine]['backend_port']:
            # check if we can retrieve ALL rois for the image
            backend_port = self.visor_controller.opts.engines_dict[engine]['backend_port']
            ses = backend_client.Session(backend_port)
            func_in = {}
            func_in['func'] = 'getRoiList'
            func_in['frame_path'] = imagename
            request = json.dumps(func_in)
            response = ses.custom_request(request)
            json_response = json.loads(response)
            if 'rois' in json_response and len(json_response['rois']) > 0:
                all_rois = json_response['rois']

        # check if an engine for 'similar' searches was specified in the settings
        # and use it as the engine for the ROIs
        roi_engine = None
        VISOR_SETTINGS = settings.VISOR
        if 'engine_for_similar_search' in VISOR_SETTINGS['engines'][engine]:
            roi_engine = VISOR_SETTINGS['engines'][engine]['engine_for_similar_search']

        # add roi to URL, if available
        imgurl = imloc
        if roi and isinstance(roi, str):
            # if the roi comes as a string, it should be as x1_y1_x2_y1_x2_y2_x1_y2_x1_y1,
            # where (x1,y1) corresponds to the top-left corner of the ROI and (x2,y2) to
            # the bottom-right corner. Split it here in preparatation for rendering.
            roi = roi.split('_')

        # format metadata to make it look nicer in the page
        metadata = self.visor_controller.metadata_handler.get_meta_from_fname(imagename, dsetname)
        try:
            # the metadata comes from the "file_attributes" column of the metadata CSV file, so
            # it should be a list of tuples. The parsing below should fail otherwise, and then
            # the raw metadata will be rendered
            if isinstance(metadata, type({}.items())):
                formatted_metadata = '<ul>'
                iii_source = ''
                for item in metadata:
                    if 'IIIF Source' not in item[0]:
                        formatted_metadata += '<li>%s: %s</li>' % (item[0], item[1])
                    else:
                        iii_source =  '<li>%s</li>' % ('<a href="' + item[1] +
                         '" target="_blank"><img src="static/images/logo-iiif.png" alt="Open IIIF manifest"></a></img>')
                formatted_metadata += '</ul>'
            metadata = formatted_metadata.replace('<ul>', '<ul>' + iii_source)
        except:
            pass

        # set up rendering context and render the page
        context = {
        'HOME_LOCATION': home_location,
        'QUERY_ID': query_id,
        'DATASET_NAME': dsetname,
        'PAGE': page,
        'ROI_ENGINE' : roi_engine,
        'ENGINE': engine,
        'AVAILABLE_ENGINES' : available_engines,
        'IMAGE_NAME' : imagename,
        'IMAGE_URL': imgurl,
        'IMAGE_LOCATION' : imloc,
        'IMAGE_WIDTH' : imwidth,
        'IMAGE_HEIGHT' : imheight,
        'IMAGE_FORMAT' : imformat,
        'ROI': roi,
        'ROIS': all_rois,
        'SELECT_ROI' : self.visor_controller.opts.select_roi,
        'DSET_RES_ID': dsetresid,
        'METADATA': metadata
        }
        return render_to_response(template, context)

