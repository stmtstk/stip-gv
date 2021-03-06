# -*- coding: utf-8 -*-
import datetime
import xmltodict
import md5
import traceback
import StringIO
import json
from xml.dom.minidom import parseString
from stix.core.stix_package import STIXPackage
from django.http.response import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from core.common import get_text_field_value
from core.api.rs import Ctirs
from core.policy.policy import get_policy, get_policy_communities
from core.taxii.taxii import Taxii
from ctim.constant import SESSION_EXPIRY

def get_sharing_ajax_get_draw_data_package_id(request):
    return get_text_field_value(request,'package_id',default_value='')
def get_sharing_ajax_get_draw_data_community(request):
    return get_text_field_value(request,'community',default_value='')
def get_sharing_ajax_updatefile_package_id(request):
    return get_text_field_value(request,'package_id',default_value='')
def get_sharing_ajax_updatefile_stix_version(request):
    return get_text_field_value(request,'stix_version',default_value='')
def get_sharing_ajax_updatefile_content(request):
    return get_text_field_value(request,'content',default_value='')
def get_sharing_ajax_get_raw_stix_package_id(request):
    return get_text_field_value(request,'package_id',default_value='')
def get_sharing_ajax_get_upload_stix_vendor_name(request):
    return get_text_field_value(request,'upload_vendor_name',default_value=None)
def get_sharing_ajax_get_upload_stix_package_name(request):
    return get_text_field_value(request,'upload_package_name',default_value=None)
def get_sharing_ajax_save_send_taxi_xml(request):
    return get_sharing_ajax_updatefile_content(request)
def get_sharing_ajax_save_send_taxi_taxii_name(request):
    return get_text_field_value(request,'taxii_name',default_value=None)

def get_sharing_ajax_change_stix_comment_package_id(request):
    return get_text_field_value(request,'package_id',default_value=None)

def get_sharing_ajax_change_stix_comment_stix_comment(request):
    return get_text_field_value(request,'comment',default_value='',is_trim_end_space=True)

#Sharing Viewの閲覧権限を持っているか?
def check_allow_sharing_view(request):
    stip_user = request.user
    user = stip_user.gv_auth_user
    #activeユーザー以外はエラー
    if stip_user.is_active == False:
        r = {'status': 'NG',
             'message' : 'You account is inactive.'}
        return JsonResponse(r,safe=False)
    #sharingビュー閲覧許可がない場合はエラー
    if user.is_sharing_view == False:
        r = {'status': 'NG',
             'message' : 'No permission.'}
        return JsonResponse(r,safe=False)
    return None

@csrf_protect
#Commment文の反映
def change_stix_comment(request):
    request.session.set_expiry(SESSION_EXPIRY)
    #GET以外はエラー
    if request.method != 'POST':
        r = {'status': 'NG',
             'message' : 'Invalid HTTP method'}
        return JsonResponse(r,safe=False)
    r = check_allow_sharing_view(request)
    if r is not None:
        return r
    #package_id取得
    package_id = get_sharing_ajax_change_stix_comment_package_id(request)
    #stix_commment取得
    stix_comment = get_sharing_ajax_change_stix_comment_stix_comment(request)
    if ((package_id is None) or (stix_comment is None)):
        r = {'status': 'NG',
             'message' : 'Invalid parameter.'}
        return JsonResponse(r,safe=False)
    if (len(stix_comment) >10240):
        r = {'status': 'NG',
             'message' : 'Exceeded the max length of Comment.'}
        return JsonResponse(r,safe=False)
    try:
        #Ctirsクラスのインスタンスを作成
        ctirs = Ctirs(request)
        #table表示用コメント作成
        ctirs.put_stix_comment(package_id,stix_comment)
        display_comment = create_display_comment(stix_comment)
        r = {'status': 'OK',
             'message': 'Success.',
             'display_comment': display_comment}
    except Exception as e:
        print 'Excepton:' + str(e)
        r = {'status': 'NG',
             'message' : str(e)}
    finally:
        return JsonResponse(r,safe=False)

#Comment文取得
def get_stix_comment(request):
    request.session.set_expiry(SESSION_EXPIRY)
    #GET以外はエラー)
    if request.method != 'GET':
        r = {'status': 'NG',
             'message' : 'Invalid HTTP method'}
        return JsonResponse(r,safe=False)
    r = check_allow_sharing_view(request)
    if r is not None:
        return r
    #package_id
    package_id = get_sharing_ajax_change_stix_comment_package_id(request)

    if ((package_id is None)):
        r = {'status': 'NG',
             'message' : 'Invalid parameter.'}
        return JsonResponse(r,safe=False)
    try:
        #Ctirsクラスのインスタンスを作成
        ctirs = Ctirs(request)
        #package_idと一致するcommentを取得
        data = ctirs.get_stix_file(package_id)
        if data is None:
            raise Exception('No data')
        r = {'status': 'OK',
             'comment' : data['comment'] }
    except Exception as e:
        print 'Excepton:' + str(e)
        r = {'status': 'NG',
             'message' : str(e)}
    finally:
        return JsonResponse(r,safe=False)

#辞書形式が　STIX 2.x 形式であるか判定する
def _is_stix2_(dict_):
    #STIX 2.x であるかの判定を行う
    v2_flag = False
    if  dict_.has_key('type') == True and dict_['type'] == u'bundle':
        v2_flag = True
    return v2_flag

def get_draw_data(request):
    request.session.set_expiry(SESSION_EXPIRY)
    #GET以外はエラー
    if request.method != 'GET':
        r = {'status': 'NG',
             'message' : 'Invalid HTTP method'}
        return JsonResponse(r,safe=False)
    r = check_allow_sharing_view(request)
    if r is not None:
        return r
    try:
        #package_id名取得
        package_id = get_sharing_ajax_get_draw_data_package_id(request)
        #community名取得
        community = get_sharing_ajax_get_draw_data_community(request)
        #Ctirsクラスのインスタンスを作成
        ctirs = Ctirs(request)
        #GetPolicy相当呼び出し
        rules = get_policy(community)
        #REST_API から STIX の json イメージを取得
        dict_ =  ctirs.get_stix_file_stix(package_id)

        #STIX 2.x であるかの判定を行う
        v2_flag = _is_stix2_(dict_)

        r = {'status': 'OK',
             'rules' : rules,
             'message' : 'Success.'}
        if v2_flag == True:
            #STIX 2.x の場合
            r['json'] = dict_
            r['stix_version'] = '2.0'
        else:
            #STIX 1.x の場合
            #json から XML イメージを返却
            xml = STIXPackage.from_dict(dict_).to_xml()
            r['xml'] = xml
            r['stix_version'] = '1.2'
    except Exception as e:
        traceback.print_exc()
        r = {'status': 'NG',
             'message' : str(e)}
    finally:
        return JsonResponse(r,safe=False)

@csrf_protect
def get_raw_stix(request):
    request.session.set_expiry(SESSION_EXPIRY)
    #GET以外はエラー
    if request.method != 'GET':
        r = {'status': 'NG',
             'message' : 'Invalid HTTP method'}
        return JsonResponse(r,safe=False)
    r = check_allow_sharing_view(request)
    if r is not None:
        return r
    try:
        #package_id取得
        package_id = get_sharing_ajax_get_raw_stix_package_id(request)
        #Ctirsクラスのインスタンスを作成
        ctirs = Ctirs(request)
        #STIXファイルの中身を取得
        j = ctirs.get_stix_file_stix(package_id)
        #STIX 2.x であるかの判定を行う
        v2_flag = _is_stix2_(j)
        if v2_flag == True:
            #返却json
            r = {'status': 'OK',
                'message' : 'Success.',
                'stix_version' : '2.0',
                'contents' : j}
        else:
            stix_package = STIXPackage.from_dict(j)
            #返却json
            r = {'status': 'OK',
                'message' : 'Success.',
                'stix_version' : '1.2',
                'contents' : stix_package.to_xml()}
    except Exception as e:
        traceback.print_exc()
        r = {'status': 'NG',
             'message' : str(e)}
    finally:
        return JsonResponse(r,safe=False)

#返却値はjson/ファイル名/ファイルの中身
def save_redacted_stix_file(request):
    #GET以外はエラー
    if request.method != 'POST':
        r = {'status': 'NG',
             'message' : 'Invalid HTTP method'}
        return r,None,None
    r = check_allow_sharing_view(request)
    if r is not None:
        return r
    try:
        #package_id取得
        package_id = get_sharing_ajax_updatefile_package_id(request)
        #stix_version 取得
        stix_version = get_sharing_ajax_updatefile_stix_version(request)
        #contentイメージ文字列取得
        content = get_sharing_ajax_updatefile_content(request).encode('utf-8')
        #編集(redactなど)のファイルを作成
        if stix_version.startswith('1.') == True:
            content,filename = update_stix_file_v1(package_id,content)
        if stix_version.startswith('2.') == True:
            content,filename = update_stix_file_v2(package_id,content)
        r = {'status': 'OK',
             'message' : 'Success.'}
        return r,content,filename
    except Exception as e:
        traceback.print_exc()
        r = {'status': 'NG',
             'message' : str(e)}
        return r,None,None

#Download する stix file を作成する (STIX 1.x)
def update_stix_file_v1(pacakge_id,content):
    #文字列イメージの引数のxmlをxml形式にして、インデントを揃えてダウンロードする
    file_path = get_file_name_from_package_id(pacakge_id) + '.xml'
    output = StringIO.StringIO(content)
    #xml整形して再書き込み
    p = STIXPackage.from_xml(output)
    #中身とファイル名を返却
    return p.to_xml(),file_path

#Download する stix file を作成する (STIX 2.x)
def update_stix_file_v2(pacakge_id,content):
    #ファイル名を返却
    file_path = get_file_name_from_package_id(pacakge_id) + '.json'
    j = json.loads(content)
    j_str = json.dumps(j,indent=4)
    return j_str,file_path

def get_file_name_from_package_id(package_id):
    return package_id.replace(':','--')

@csrf_protect
def get_upload_stix(request):
    request.session.set_expiry(SESSION_EXPIRY)
    #POST以外はエラー
    if request.method != 'POST':
        r = {'status': 'NG',
             'message' : 'Invalid HTTP method'}
        return JsonResponse(r,safe=False)
    r = check_allow_sharing_view(request)
    if r is not None:
        return r
    try:
        #package_name名取得
        package_name  = get_package_name_from_stix(request)
        r = {'status': 'OK',
             'package_name' : package_name,
             'message' : 'Success.'}
    except Exception as e:
        traceback.print_exc()
        print 'Exception:' + str(e)
        r = {'status': 'NG',
             'message' : str(e)}
    finally:
        return JsonResponse(r,safe=False)

@csrf_protect
#taxiiに送信する
def send_taxii(request):
    request.session.set_expiry(SESSION_EXPIRY)
    #POST以外はエラー
    if request.method != 'POST':
        r = {'status': 'NG',
             'message' : 'Invalid HTTP method'}
        return JsonResponse(r,safe=False)
    r = check_allow_sharing_view(request)
    if r is not None:
        return r
    xml = parseString(get_sharing_ajax_save_send_taxi_xml(request).encode('utf-8')).toprettyxml(encoding='utf-8')
    taxii_name = get_sharing_ajax_save_send_taxi_taxii_name(request)
    try:
        taxii = Taxii(taxii_name)
        msg = taxii.push(xml)
        if msg == '':
            r = {'status': 'OK',
                 'message' : 'No message.'}
        else:
            r = {'status': 'OK',
                 'message' : msg}
    except Exception as e:
        traceback.print_exc()
        print 'Exception:' + str(e)
        r = {'status': 'NG',
             'message' : str(e)}
    finally:
        return JsonResponse(r,safe=False)

def get_package_name_no_specify_package_name(content,vendor_name):
    #xml->OrderedDict変換
    d = xmltodict.parse(content,attr_prefix=u'ATTR')
    #1.stix:Campaignsタグから
    #→廃止

    #2.stix:STIX_Headerタグから
    package_name = get_package_name_from_stix_header_tag(d)
    if package_name is not None:
        return package_name
    #3.stix:STIX_Pacakgeから
    package_name = get_package_name_from_stix_package_tag(d)
    if package_name is not None:
        return package_name
    #4.vendor_sourceとハッシュ値から
    return get_pacakge_name_from_vendor_source_hash(vendor_name,content)

def get_package_name_from_stix(request):
    #1.エンドユーザー指定から
    package_name = get_sharing_ajax_get_upload_stix_package_name(request)
    if package_name is not None:
        return package_name

    #stixファイルから取得
    stix_file = request.FILES['stix']
    content = stix_file.read()
    vendor_name = get_sharing_ajax_get_upload_stix_vendor_name(request)
    return get_package_name_no_specify_package_name(content,vendor_name)

#stix:STIX_Headerタグからpackage名が取得可能か？
def get_package_name_from_stix_header_tag(d):
    try:
        return d[u'stix:STIX_Package'][u'stix:STIX_Header'][u'stix:Title']
    except:
        return None

#stix:STIX_Pacakgeタグからpackage名が取得可能か？
def get_package_name_from_stix_package_tag(d):
    try:
        return d[u'stix:STIX_Package'][u'ATTRid']
    except:
        return None

#vendor_soruceとハッシュ値
def get_pacakge_name_from_vendor_source_hash(vendor_soruce,content):
    return '%s_%s' % (vendor_soruce,md5.new(content).hexdigest())

@login_required
@csrf_protect
def create_language_content(request):
    request.session.set_expiry(SESSION_EXPIRY)
    #POST以外はエラー
    if request.method != 'POST':
        r = {'status': 'NG',
             'message' : 'Invalid HTTP method'}
        return JsonResponse(r,safe=False)
    try:
        content = request.POST[u'content']
        object_ref = request.POST[u'object_ref']
        language = request.POST[u'language']
        selector = request.POST[u'selector']
        language_content = {
            u'content': content,
            u'selector': selector,
            u'language': language,
        }
        language_contents = [language_content]

        #Ctirsクラスのインスタンスを作成
        ctirs = Ctirs(request)
        #language_content 作成
        ctirs.post_language_contents(object_ref,language_contents)
        resp = {'status': 'OK',
             'message' : 'Success!!'}
    except Exception as e:
        traceback.print_exc()
        resp = {'status': 'NG',
             'message' : e.message}
    finally:
        return JsonResponse(resp,safe=False)

@login_required
def get_package_table(request):
    request.session.set_expiry(SESSION_EXPIRY)
    #GET以外はエラー
    if request.method != 'GET':
        r = {'status': 'NG',
             'message' : 'Invalid HTTP method'}
        return JsonResponse(r,safe=False)
    r = check_allow_sharing_view(request)
    if r is not None:
        return r
    try:
        #ajax parameter取得
        sEcho = request.GET['sEcho']
        #表示する長さ
        iDisplayLength = int(request.GET['iDisplayLength'])
        #表示開始位置インデックス
        iDisplayStart = int(request.GET['iDisplayStart'])
        #検索文字列
        sSearch = request.GET['sSearch']
        #ソートする列
        sort_col = int(request.GET['iSortCol_0'])
        #ソート順番 (desc指定で降順)
        sort_dir = request.GET['sSortDir_0']

        #Ctirsクラスのインスタンスを作成
        ctirs = Ctirs(request)
        #ajax呼び出し
        data = ctirs.get_package_list_for_sharing_table(iDisplayLength,iDisplayStart,sSearch,sort_col,sort_dir)
        if data is None:
            raise Exception('No data')

        aaData = []
        for item in data['data']:
            package_id = item['package_id']
            package_name = item['package_name']
            l = []
            l.append('<input type="checkbox" package_id="%s" class="delete-checkbox"/>' % (package_id))
            l.append('<a package_id="%s" screen_user="%s" class="stix-comment-dialog">%s</a>' % (package_id,request.user,create_display_comment(item['comment'])))
            l.append('<a package_id="%s" class="csv-download"><span class="glyphicon glyphicon-cloud-download"></span></a>' % (package_id))
            l.append('<a package_id="%s" class="draw-package">%s</a>' % (package_id,package_name))
            l.append(item['input_community'])
            communities = get_policy_communities().split(',')
            for community in communities:
                html = '<a href="#" class="review-link" package_id="%s" community="%s"><label>[Click to Review]</label></a>'  % (package_id,community)
                l.append(html)
            aaData.append(l)

        #Data 作成
        resp = {}
        resp['iTotalRecords'] = int(data['iTotalRecords'])
        resp['iTotalDisplayRecords'] = int(data['iTotalDisplayRecords'])
        resp['sEcho'] = sEcho
        resp['aaData'] = aaData
    except Exception as e:
        traceback.print_exc()
        resp = {'status': 'NG',
             'message' : e.message}
    finally:
        return JsonResponse(resp,safe=False)
    
#データが日付か判断
def check_date(date):
    try:
        datetime.datetime.strptime(date,'%Y/%m/%d %H:%M:%S')
        return True
    except ValueError:
        return False
    
#table表示用の文字列作成
def create_display_comment(comment):
    display_comment = 'Click to comment.'
    #データを改行で分割
    split_indention = comment.split('\n')
    #「>>YYYY/MM/DD HH/MM/SS by」のフォーマットか確認
    for sentence in split_indention:
        if(sentence[0:2]=='>>' and
            check_date(sentence[2:21])==True and
            sentence[22:24]=='by'):
            continue
        #空文字、タブ、半角スペース、全角スペースを確認
        elif(sentence == ''
            or sentence == '\t'
            or sentence == ' '
            or sentence == u'\u3000' ):
            continue
        else:
            display_comment = sentence
            break
    return display_comment