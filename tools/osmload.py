import glob, xml.etree.ElementTree as ET, pickle, sys, os
def load(dirpath, cache):
    if os.path.exists(cache):
        return pickle.load(open(cache,'rb'))
    nodes, ways, rels = {}, {}, {}
    for f in sorted(glob.glob(os.path.join(dirpath,'*.osm'))):
        for ev, el in ET.iterparse(f, events=('end',)):
            if el.tag == 'node':
                nodes[int(el.get('id'))] = (float(el.get('lat')), float(el.get('lon')))
                el.clear()
            elif el.tag == 'way':
                ways[int(el.get('id'))] = {'n':[int(n.get('ref')) for n in el.findall('nd')], 't':{t.get('k'):t.get('v') for t in el.findall('tag')}}
                el.clear()
            elif el.tag == 'relation':
                rels[int(el.get('id'))] = {'m':[(m.get('type'), int(m.get('ref')), m.get('role')) for m in el.findall('member')], 't':{t.get('k'):t.get('v') for t in el.findall('tag')}}
                el.clear()
    d = (nodes, ways, rels)
    pickle.dump(d, open(cache,'wb'))
    return d
