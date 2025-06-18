#!/usr/bin/env python3
import os,sys,glob,time,csv,math,pprint,shutil,fnmatch
import re
import nibabel as nib
from parsl.app.app import python_app
from os.path import *
from mappertrac.subscripts import *
from fnmatch import fnmatch
from dipy.denoise.localpca import mppca

@python_app(executors=['worker'])
def run_freesurfer(params):

    input_dir = params['input_dir']
    sdir = params['work_dir']
    ID = params['ID']
    stdout = params['stdout']
    ncores = params['nnodes'] # For grid engine on UCSF Wynton

    start_time = time.time()
    start_str = f'''
=====================================
{get_time_date()}
Started step 1: freesurfer
Arguments: 
{pprint.pformat(params, width=1)}
=====================================
'''
    write(stdout, start_str)
    print(start_str)

    write(stdout, f'The sdir is: {sdir}')
    write(stdout, f'The input_dir is: {input_dir}')
    write(stdout, f'The ID is: {ID}')
    smart_mkdir(sdir)

    # Check available input dwi image. Add study specific naming condition if needed.
    if isfile(join(sdir, f'{ID}_b1300_dwi_eddy_resamp_denoised.nii.gz')):
        input_dwi = join(sdir, f'{ID}_b1300_dwi_eddy_resamp_denoised.nii.gz')
    elif isfile(join(sdir, f'{ID}_space-orig_desc-b2000_dwi_eddy_denoised.nii.gz')):
        input_dwi = join(sdir, f'{ID}_space-orig_desc-b2000_dwi_eddy_denoised.nii.gz')
    elif isfile(join(sdir, f'{ID}_dwi.nii.gz')):
        input_dwi = join(sdir, f'{ID}_dwi.nii.gz')
    
    # Check available reverse phase-encoding b0. Optional availability.
    if isfile(join(sdir, f'{ID}_b0_dir-rev_dwi.nii.gz')):
        input_rev = join(sdir, f'{ID}_b0_dir-rev_dwi.nii.gz')

    # Check corresponding bval and bvec
    if isfile(join(sdir, f'{ID}_dwi.bval')):
        input_bval = join(sidr, f'{ID}_dwi.bval')
    elif isfile(join(sdir, f'bvals')):
        input_bval = join(sdir, f'bvals')

    if isfile(join(sdir, f'{ID}_dwi.bvec')):
        input_bvec = join(sdir, f'{ID}_dwi.bvec')
    elif isfile(join(sdir, f'bvecs')):
        input_bvec = join(sdir, f'bvecs')

    # Check available T1.
    if isfile(join(sdir, f'{ID}_t1w.nii.gz')):
        input_T1 = join(sdir, f'{ID}_t1w.nii.gz')
    elif isfile(join(sdir, f'{ID}_T1w.nii.gz')):
        input_T1 = join(sdir, f'{ID}_T1w.nii.gz')

    write(stdout, f'The input_dwi is: {input_dwi}')
    write(stdout, f'The input_bval is: {input_bval}')
    write(stdout, f'The input_bvec is: {input_bvec}')
    write(stdout, f'The input_T1 is: {input_T1}')

    all_inputs_exist = True    
    for file in [input_dwi, input_bval, input_bvec, input_T1]:
        if not exists(file):
            all_inputs_exist = False
            write(stdout, f'Missing file {file} !!')

    if not all_inputs_exist:
        input_dwis = glob(join(input_dir, 'dwi', f'{ID}_*dwi.nii.gz'))
        input_dwis_count = len((input_dwis))
        if (input_dwis_count == 1) and (isfile(input_dwis[0])):
            input_dwi = input_dwis[0]
            input_dwi_filename = split(input_dwi)[1]
            ID_full = input_dwi_filename[:-11]
        elif (input_dwis_count == 0):
            raise FileNotFoundError(f'No input dwi NIFTI files were found')
        elif (input_dwis_count >= 2):
            raise ValueError(f'Mappertrac found {input_dwis_count} files for dwi input, but currently supports only one input')
        input_rev = join(input_dir, 'dwi', f'{ID_full}_dwi_rev.nii.gz') # this may need reversal of the dir-{dir} tag in the ID_full string
        input_bval = join(input_dir, 'dwi', f'{ID_full}_dwi.bval')
        input_bvec = join(input_dir, 'dwi', f'{ID_full}_dwi.bvec')
        if isfile(join(input_dir, 'anat', f'{ID}_run-01_T1w.nii.gz')):
            input_T1 = join(input_dir, 'anat', f'{ID}_run-01_T1w.nii.gz')
        else:
            input_T1 = join(input_dir, 'anat', f'{ID}_T1w.nii.gz')
        for _ in [input_dwi, input_bval, input_bvec, input_T1]:
            assert exists(_), f'Missing file {_}'

        smart_mkdir(sdir)
        work_dwi = join(sdir, 'hardi.nii.gz')
        work_bval = join(sdir, 'bvals')
        work_bvec = join(sdir, 'bvecs')
        work_T1 = join(sdir, 'T1.nii.gz')
        smart_copy(input_dwi, work_dwi)
        smart_copy(input_bval, work_bval)
        smart_copy(input_bvec, work_bvec)
        smart_copy(input_T1, work_T1)

        # Save NIfTI files in BIDS rawdata directory
        #rawdata_dir = sdir.replace('/derivatives/', '/rawdata/')
        #smart_copy(input_dir, rawdata_dir)
    else:
        smart_mkdir(sdir)
        work_dwi = input_dwi
        work_bval = input_bval
        work_bvec = input_bvec
        work_T1 = input_T1
        write(stdout, f'All input files already exist in the work_dir. Proceed to preprocessing.')
        
    ##################################
    # dti-preproc
    ##################################

    if exists(join(sdir, f'{ID}_*_eddy*.nii.gz')): 
        write(stdout, "Work dwi was eddy output to begin with.")
        # Variable brain_mask was named bet_mask in previous mappertrac versions.
        brain_mask = join(sdir, f'{ID}_*_eddy_brain_mask.nii.gz')
        if not exists(brain_mask):
            write(stdout, "Missing the brain mask file!")
    else:
        #---------------#
        # Preprocessing #
        #---------------#
        
        # MPPCA denoise
        im_noise = nib.load(work_dwi).get_fdata()
        im_denoised = mppca(im_noise, patch_radius=2)
        im_output_name = os.path.basename(work_dwi).replace(".nii.gz", "_denoised.nii.gz")
        work_dwi_denoised = join(sdir, im_output_name)
        nib.save(nib.Nifti1Image(im_denoised, affine=nib.load(work_dwi).affine), work_dwi_denoised)

        # Identify b0 volumes in work_dwi
        bval_txt = open(work_bval, 'r')
        bval_list = bval_txt.read().split()
        b0_idx = [idx for idx, v in enumerate(bval_list) if v == '0']
        write(stdout, f'B0 index: {b0_idx}')

        # Reorganize work_dwi_denoised by having the average b0 followed by diffusion volumes
        vol_prefix = join(sdir, 'vol')
        run(f'fslsplit {work_dwi_denoised} {vol_prefix}', params)
        split_list = [f for f in os.listdir(sdir) if fnmatch(f, 'vol*.nii.gz')]
        split_list_sorted = sorted(split_list) # This is necessary because os.listdir does not return files in sorted name order - 12/13/22

        b0_list = []
        b0_list_dirs = []
        for idx in b0_idx:
            b0_file = split_list_sorted[int(idx)]
            b0_file_dir = join(sdir, b0_file)
            b0_list.append(b0_file)
            b0_list_dirs.append(b0_file_dir)

        diff_list = split_list_sorted
        diff_list_dirs = []
        for idx in b0_list:
            diff_list.remove(idx)
        for vol in diff_list:
            vol_dir = join(sdir, vol)
            diff_list_dirs.append(vol_dir)

        b0_list_names = ' '.join(b0_list_dirs)
        diff_list_names = ' '.join(diff_list_dirs)
        b0s = join(sdir, 'b0s.nii.gz')
        b0_avg = join(sdir, 'b0_avg.nii.gz')
        dwi_reorg = join(sdir, 'dwi_reorg.nii.gz')
        run(f'fslmerge -t {b0s} {b0_list_names}', params)
        run(f'fslmaths {b0s} -Tmean {b0_avg}', params)
        run(f'fslmerge -t {dwi_reorg} {b0_avg} {diff_list_names}', params)

        # Write reorganized bvals
        work_bval_reorg = join(sdir, 'bvals_reorg')
        with open(work_bval_reorg, 'w') as bval_txt_reorg:
            bval_list_reorg = [b for idx, b in enumerate(bval_list) if b != '0']
            bval_txt_reorg.write('0')
            for i in range(len(bval_list_reorg)):
                bval_txt_reorg.write(' ')
                bval_txt_reorg.write(bval_list_reorg[i])
            bval_txt_reorg.write('\n')

        # Write reorganized bvecs
        bvec_txt = open(work_bvec, 'r')
        bvec_list = bvec_txt.read().split()
        b0_idx_for_bvec = b0_idx + [i + len(bval_list) for i in b0_idx] + [i + 2 * len(bval_list) for i in b0_idx]
        bvec_list_reorg = [b for idx, b in enumerate(bvec_list) if idx not in b0_idx_for_bvec]

        work_bvec_reorg = join(sdir, 'bvecs_reorg')
        with open(work_bvec_reorg, 'w') as bvec_txt_reorg:
            bvec_txt_reorg.write('0')
            nvols_diffusion = int(len(bvec_list_reorg)/3)
            bvec_line_breaks = [nvols_diffusion, nvols_diffusion * 2]
            for i in range(len(bvec_list_reorg)):
                bvec_txt_reorg.write('\n' + '0 ') if i in bvec_line_breaks else bvec_txt_reorg.write(' ')
                bvec_txt_reorg.write(bvec_list_reorg[i])
            bvec_txt_reorg.write('\n')

        write(stdout, f'Finished reorganizing the dwi image and the bvec, bval files.')

        # Optional topup step
        data_topup = join(sdir, 'data_topup.nii.gz')

        try:
            input_rev
        except NameError:
            write(stdout, "No revPE input image available. Skipping topup. ")
            smart_copy(dwi_reorg, data_topup)
        else:
            # Define file name variables
            b0_ap = join(sdir, 'b0_ap.nii.gz')
            b0_pa = join(sdir, 'b0_pa.nii.gz')
            topup_input = join(sdir, 'b0_ap_pa.nii.gz')
            acq_file = join(sdir, 'acq.txt')
            topup_results = join(sdir, 'topup_results') # FIXME

            # cut and merge b0_ap and b0_pa for topup
            run(f'fslroi {dwi_reorg} {b0_ap} 0 1', params)
            run(f'fslroi {input_rev} {b0_pa} 0 1', params)
            run(f'fslmerge -t {topup_input} {b0_ap} {b0_pa}', params) 

            # Write a generic acquisition file
            run(f'echo "0 1 0 0.05" > {acq_file}', params)
            run(f'echo "0 -1 0 0.05" >> {acq_file}', params)

            # run topup
            run(f'topup --imain={topup_input} --datain={acq_file}, --config=b02b0_1.cnf --out={topup_results} --verbose', params)
            run(f'applytopup --imain={dwi_reorg} --datain={acq_file}, --inindex=1,2 --topup={topup_results} --out={data_topup}', params)    

        # Cleanup splitted tmp files
        smart_remove(join(sdir, 'vol*.nii.gz'))

        # Pre-eddy brain mask extraction
        b0_topup = join(sdir, f'data_topup_b0.nii.gz')
        dwi_brain = join(sdir, f'dwi_brain.nii.gz')
        brain_mask = join(sdir, f'dwi_brain_mask.nii.gz')

        run(f'fslroi {data_topup} {b0_topup} 0 1', params)
        run(f'mri_synthstrip -i {b0_topup} -o {dwi_brain} -m {brain_mask}', params)

        # FIXME Make index file for eddy

        # FSL eddy
        data_denoised_eddy = join(sdir, f'dwi_denoised_eddy.nii.gz')
        data_denoised_eddy_namebase = join(sdir, f'dwi_denoised_eddy')
        if isfile(join(sdir, f'*_topup_fieldcoef.nii.gz'):
            run(f'eddy_cuda10.2 --imain={data_topup} --mask={brain_mask} --acqp={acq_file} --index={idx_file} --bvecs={work_bvec_reorg} --bvals={work_bval_reorg} --topup={topup_results} --out={data_denoised_eddy_namebase} --niter=5 --fwhm=10,0,0,0,0 --cnr_maps --repol --estimate_move_by_susceptibility --data_is_shelled --verbose', params)
        else:
            run(f'eddy_cuda10.2 --imain={data_topup} --mask={brain_mask} --acqp={acq_file} --index={idx_file} --bvecs={work_bvec_reorg} --bvals={work_bval_reorg} --out={data_denoised_eddy_namebase} --fwhm=10,0,0,0,0 --cnr_maps --repol --data_is_shelled --verbose', params)

        # Registration based motion correction and eddy
        #eddy_prefix = join(sdir, 'data_eddy')
        #data_eddy = f'{eddy_prefix}.nii.gz'
        #bet = join(sdir, 'data_bet.nii.gz')
        #brain_mask = join(sdir, 'data_brain_mask.nii.gz')
        #data_eddy_denoised = join(sdir, f'{ID}_b1300_dwi_eddy_resamp_denoised.nii.gz')

        #if exists(data_eddy_denoised):
        #    write(stdout, "Eddy and denoised output image was found. Skipping eddy step. ")
        #    if exists(dwi_reorg):
        #        smart_copy(dwi_reorg, data_eddy)
        #    else:
        #        data_eddy = join(sdir, f'{ID}_b1300_dwi_eddy_resamp_denoised.nii.gz')
        #else:
        #    for _ in glob(f'{eddy_prefix}_tmp????.*') + glob(f'{eddy_prefix}_ref*'):
        #        smart_remove(_)

        #    run(f'fslroi {data_topup} {eddy_prefix}_ref 0 1', params)
        #    run(f'fslsplit {data_topup} {eddy_prefix}_tmp', params)

        #    timeslices = glob(f'{eddy_prefix}_tmp????.*')
        #    timeslices.sort()
        #    for _ in timeslices:
        #        run(f'flirt -in {_} -ref {eddy_prefix}_ref -nosearch -interp trilinear -o {_} -paddingsize 1', params)
        #    run(f'fslmerge -t {data_eddy} {" ".join(timeslices)}', params)
        #    run(f'bet {data_eddy} {bet} -m -f 0.3', params)

        # Post-eddy brain mask extraction: make eddy_brain_mask
        b0_eddy = join(sdir, f'dwi_denoised_eddy_b0.nii.gz')
        eddy_brain = join(sdir, f'dwi_denoised_eddy_brain.nii.gz')
        eddy_brain_mask = join(sdir, f'dwi_denoised_eddy_brain_mask.nii.gz')

        run(f'fslroi {data_denoised_eddy} {b0_eddy} 0 1', params)
        run(f'mri_synthstrip -i {b0_eddy} -o {eddy_brain} -m {eddy_brain_mask}', params)

    #--- This is the end of preprocessing ---#

    # Check available FA. If no FA is available, run dtifit to generate DTI parameters
    FA = join(sdir, f'{ID}_b1300_dwi_eddy_resamp_denoised_dti_FA.nii.gz')
    FA_alt = join(sdir, f'{ID}_space-orig_model-DTI_FA.nii.gz')
    if exists(FA):
        write(stdout, "DTI parameter FA map already exists. Skipping DTI fit. ")
    elif exists(FA_alt):
        write(stdout, "DTI parameter FA map already exists. Skipping DTI fit. ")
        FA = FA_alt
    else:
        dti_params = join(sdir, '{ID}_denoised_eddy_dti')
        dti_L1 = f'{dti_params}_L1.nii.gz'
        dti_L2 = f'{dti_params}_L2.nii.gz'
        dti_L3 = f'{dti_params}_L3.nii.gz'
        dti_MD = f'{dti_params}_MD.nii.gz'
        dti_RD = f'{dti_params}_RD.nii.gz'
        dti_MD = f'{dti_params}_MD.nii.gz'
        dti_AD = f'{dti_params}_AD.nii.gz'
        dti_FA = f'{dti_params}_FA.nii.gz'
        if exists(brain_mask):
            run(f'cat -e {work_bvec_reorg}', params)
            run(f'cat -e {work_bval_reorg}', params) 
            run(f'dtifit --verbose -k {data_eddy} -o {dti_params} -m {eddy_brain_mask} -r {work_bvec_reorg} -b {work_bval_reorg}', params)
            run(f'fslmaths {dti_L1} -add {dti_L2} -add {dti_L3} -div 3 {dti_MD}', params)
            run(f'fslmaths {dti_L2} -add {dti_L3} -div 2 {dti_RD}', params)
            smart_copy(dti_L1, dti_AD)
        else:
            write(stdout, "Warning: failed to generate masked outputs")
            raise Exception(f'Failed brain mask extraction step. Please check {stdout} for more info.')

        for _ in glob(f'{eddy_prefix}_tmp????.*') + glob(f'{eddy_prefix}_ref*'):
            smart_remove(_)
        smart_copy(dti_FA, FA)

    #############
    # recon-all #
    #############
    EDI = join(sdir, 'EDI')
    synthseg = join(sdir, f'{ID}_reconall-synthseg')
    mri = join(sdir, 'mri')
    surf = join(sdir, 'surf')
    label = join(sdir, 'label')
    stats = join(sdir, 'stats')
    scripts = join(sdir, 'scripts')
    touch = join(sdir, 'touch')

    if exists(synthseg):
        write(stdout, f'Found recon-all synthseg results.')
        synthseg_mri = join(sdir,f'{ID}_reconall-synthseg/mri')
        synthseg_surf = join(sdir,f'{ID}_reconall-synthseg/surf')
        synthseg_label = join(sdir,f'{ID}_reconall-synthseg/label')
        synthseg_stats = join(sdir,f'{ID}_reconall-synthseg/stats')
        synthseg_scripts = join(sdir,f'{ID}_reconall-synthseg/scripts')
        synthseg_touch = join(sdir,f'{ID}_reconall-synthseg/touch')
        smart_copy(synthseg_mri, mri)
        smart_copy(synthseg_surf, surf)
        smart_copy(synthseg_label, label)
        smart_copy(synthseg_stats, stats)
        smart_copy(synthseg_scripts, scripts)
        smart_copy(synthseg_touch, touch)
        
    mri_brain = join(sdir, 'mri', 'brain.mgz')
    mri_aseg = join(sdir, 'mri', 'aseg.mgz')
    if not exists(mri_aseg):
        mri_aseg = join(sdir, 'mri', 'aparc+aseg.mgz')

    if exists(synthseg):
        write(stdout, f'Parsing recon-all synthseg results and skipping recon-all.')
    elif exists(EDI):
        write(stdout, f'Detected EDI folder. Skipping recon-all.')
    elif exists(mri_brain) and exists(mri_aseg):
        write(stdout, f'Found brain mgz and aseg mgz. Skipping recon-all.')
    else:
        mri_out = join(sdir, 'mri', 'orig', '001.mgz')
        smart_mkdir(join(sdir, 'mri', 'orig'))
        run(f'mri_convert {work_T1} {mri_out}', params)
        write(stdout, f'Running Freesurfer with {ncores} cores')
        run(f'recon-all -s . -all -synthstrip -synthseg -notal-check -no-isrunning -cw256 -parallel -openmp {ncores}', params)

    ########################
    # mri_annotation2label #
    ########################
    aseg = join(sdir, 'aseg.nii.gz')
    bs = join(sdir, 'bs.nii.gz')
    FA2T1 = join(sdir, 'FA2T1.mat')
    T12FA = join(sdir, 'T12FA.mat')
    cort_label_dir = join(sdir, 'label_cortical')
    cort_vol_dir = join(sdir, 'volumes_cortical')
    cort_vol_dir_out = cort_vol_dir + '_s2fa'
    subcort_vol_dir = join(sdir, 'volumes_subcortical')
    subcort_vol_dir_out = subcort_vol_dir + '_s2fa'
    terminationmask = join(sdir, 'terminationmask.nii.gz')
    allvoxelscortsubcort = join(sdir, 'allvoxelscortsubcort.nii.gz')
    intersection = join(sdir, 'intersection.nii.gz')
    subcortical_index = [
        '10:lh_thalamus', '11:lh_caudate', '12:lh_putamen', '13:lh_pallidum', '17:lh_hippocampus', '18:lh_amygdala', '26:lh_acumbens', 
        '49:rh_thalamus', '50:rh_caudate', '51:rh_putamen', '52:rh_pallidum', '53:rh_hippocampus', '54:rh_amygdala', '58:rh_acumbens',
    ]

    EDI_allvols = join(EDI, 'allvols')

    smart_mkdir(cort_label_dir)
    smart_mkdir(cort_vol_dir)
    smart_mkdir(subcort_vol_dir)
    smart_mkdir(cort_vol_dir_out)
    smart_mkdir(subcort_vol_dir_out)
    smart_mkdir(EDI)
    smart_mkdir(EDI_allvols)

    # Will try multiple versions of registration	
    reconall_T1 = join(sdir, f'{ID}_t1w_reconall.nii.gz')
    run(f'mri_convert {mri_brain} {reconall_T1} ', params)
    run(f'mri_convert {mri_aseg} {aseg}', params)
    run(f'flirt -in {FA} -ref {reconall_T1} -omat {FA2T1}', params)
    run(f'convert_xfm -omat {T12FA} -inverse {FA2T1}', params)
    run(f'mri_annotation2label --subject . --hemi rh --annotation aparc.DKTatlas --outdir {cort_label_dir}', params)
    run(f'mri_annotation2label --subject . --hemi lh --annotation aparc.DKTatlas --outdir {cort_label_dir}', params)
    # FIX ME: check if we need to change the path of aseg

    for label in glob(join(cort_label_dir, '*.label')):
        vol_file = join(cort_vol_dir, splitext(split(label)[1])[0] + '.nii.gz')
        run(f'mri_label2vol --label {label} --temp {reconall_T1} --identity --o {vol_file}', params)

    for line in subcortical_index:
        num = line.split(':')[0].lstrip().rstrip()
        area = line.split(':')[1].lstrip().rstrip()
        area_out = join(subcort_vol_dir, area + '.nii.gz')
        write(stdout, f'Processing {area}.nii.gz')
        run(f'fslmaths {aseg} -uthr {num} -thr {num} -bin {area_out}', params)

    for volume in glob(join(cort_vol_dir, '*.nii.gz')):
        out_vol = join(cort_vol_dir_out, splitext(splitext(split(volume)[1])[0])[0] + '_s2fa.nii.gz')
        write(stdout, f'Processing {split(volume)[1]} -> {split(out_vol)[1]}')
        run(f'flirt -in {volume} -ref {FA} -out {out_vol}  -applyxfm -init {T12FA}', params)
        run(f'fslmaths {out_vol} -thr 0.2 -bin {out_vol} ', params)

    for volume in glob(join(subcort_vol_dir, '*.nii.gz')):
        out_vol = join(subcort_vol_dir_out, splitext(splitext(split(volume)[1])[0])[0] + '_s2fa.nii.gz')
        write(stdout, f'Processing {split(volume)[1]} -> {split(out_vol)[1]}')
        run(f'flirt -in {volume} -ref {FA} -out {out_vol}  -applyxfm -init {T12FA}', params)
        run(f'fslmaths {out_vol} -thr 0.2 -bin {out_vol}', params)

    run(f'fslmaths {FA} -mul 0 {bs}', params)  # For now we fake a bs.nii.gz file
    work_FA = join(sdir, 'FA.nii.gz')
    smart_copy(FA, work_FA)
    maskseeds(sdir, join(cort_vol_dir + '_s2fa'), join(cort_vol_dir + '_s2fa_m'), 0.05, 1, 1, params)
    maskseeds(sdir, join(subcort_vol_dir + '_s2fa'), join(subcort_vol_dir + '_s2fa_m'), 0.05, 0.4, 0.4, params)
    saveallvoxels(sdir, join(cort_vol_dir + '_s2fa_m'), join(subcort_vol_dir + '_s2fa_m'), allvoxelscortsubcort, params)

    ####################
    # termination mask #
    ####################
    smart_remove(terminationmask)
    run(f'fslmaths {FA} -uthr .15 {terminationmask}'.format(FA, terminationmask), params)
    run(f'fslmaths {terminationmask} -add {bs} {terminationmask}', params)
    run(f'fslmaths {terminationmask} -bin {terminationmask}', params)
    run(f'fslmaths {terminationmask} -mul {allvoxelscortsubcort} {intersection}', params)
    run(f'fslmaths {terminationmask} -sub {intersection} {terminationmask}', params)
    for file in glob(join(sdir, 'volumes_cortical_s2fa','*.nii.gz')):
        shutil.copy(file, EDI_allvols)
    for file in glob(join(sdir, 'volumes_subcortical_s2fa','*.nii.gz')):
        shutil.copy(file, EDI_allvols)
    validate(terminationmask, params)
    #update_permissions(sdir, params)

    write(join(sdir, 'S1_COMPLETE'))
    
    finish_str = f'''
=====================================
{get_time_date()}
Finished step 1: freesurfer
Arguments: 
{pprint.pformat(params, width=1)}
Total time: {get_time_string(time.time() - start_time)} (HH:MM:SS)
=====================================
'''
    write(stdout, finish_str)
    print(finish_str)
