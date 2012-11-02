# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the testkraut package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
""""""

__docformat__ = 'restructuredtext'

import operator

_tag2fx = {}

def get_fingerprinters(tag):
    if not len(_tag2fx):
        # charge
        _tag2fx.update({
            'volumetric image': [fp_volume_image]
        })
    return _tag2fx.get(tag, [])

def fp_volume_image(fname, fp):
    # this version needs an increment whenever this implementation changes
    fp['version'] = 0
    import nibabel as nb
    import numpy as np
    from scipy.ndimage import measurements as msr
    img = nb.load(fname)
    img_data = img.get_data().astype('float') # float for z-score
    # keep a map where the original data is larger than zero
    zero_thresh = img_data > 0
    # global zscore 
    img_std = img_data.std()
    img_mean = img_data.mean()
    fp['std'] = img_std
    fp['mean'] = img_mean
    fp['min'] = img_data.min()
    fp['max'] = img_data.max()
    img_data -= img_mean
    img_data /= img_std
    # normalized luminance histogram (needs zscores)
    luminance_hist_params = (-3, 3, 7)
    fp['luminance_histogram_[%i,%i,%i]' % luminance_hist_params] = \
            np.histogram(img_data, normed=True,
                         bins=np.linspace(*luminance_hist_params))[0]
    if not img_std:
        # no variance, nothing to do
        return
    # perform thresholding at various levels and compute descriptive
    # stats of the resulting clusters
    clusters = np.empty(img_data.shape, dtype=int)
    for thresh in (zero_thresh, 2.0, 4.0, 8.0, -2.0, -4.0, -8.0):
        # create a binarized map for the respective threshold
        if not isinstance(thresh, float):
            thresh_map = thresh
            thresh = 'orig_zero'
        else:
            if thresh < 0:
                thresh_map = img_data < thresh
            else:
                thresh_map = img_data > thresh
        nclusters = msr.label(thresh_map, output=clusters)
        # sort by cluster size
        cluster_sizes = [(cl, np.sum(clusters == cl))
                                for cl in xrange(1, nclusters + 1)]
        cluster_sizes = sorted(cluster_sizes,
                               key=operator.itemgetter(1),
                               reverse=True)
        # how many clusters to report
        max_nclusters = 3
        if not len(cluster_sizes):
            # nothing to report, do not clutter the dict
            continue
        clinfo = {}
        fp['thresh_%s' % thresh] = clinfo
        clinfo['nclusters'] = nclusters
        # only for the biggest clusters
        cl_id = 0
        for cl_label, cl_size in cluster_sizes[:max_nclusters]:
            cl_id += 1
            cli = dict(size=cl_size)
            clinfo['cluster_%i' % cl_id] = cli
            # center of mass of the cluster extent (ignoring actual values)
            cli['extent_ctr_of_mass'] = \
                    msr.center_of_mass(thresh_map, labels=clusters,
                                       index=cl_label)
            # center of mass of the cluster considering actual values
            cli['ctr_of_mass'] = msr.center_of_mass(img_data,
                                                    labels=clusters,
                                                    index=cl_label)
            if isinstance(thresh, float) and thresh < 0:
                # position of minima
                pos = msr.minimum_position(img_data, labels=clusters, index=cl_label)
                cli['min_pos'] = pos
                cli['min'] = img_data[pos]
            else:
                # position of maxima
                pos = msr.maximum_position(img_data, labels=clusters, index=cl_label)
                cli['max_pos'] = pos
                cli['max'] = img_data[pos]