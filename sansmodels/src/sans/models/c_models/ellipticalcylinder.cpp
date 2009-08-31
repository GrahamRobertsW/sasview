/**
	This software was developed by the University of Tennessee as part of the
	Distributed Data Analysis of Neutron Scattering Experiments (DANSE)
	project funded by the US National Science Foundation.

	If you use DANSE applications to do scientific research that leads to
	publication, we ask that you acknowledge the use of the software with the
	following sentence:

	"This work benefited from DANSE software developed under NSF award DMR-0520547."

	copyright 2008, University of Tennessee
 */

/**
 * Scattering model classes
 * The classes use the IGOR library found in
 *   sansmodels/src/libigor
 *
 *	TODO: refactor so that we pull in the old sansmodels.c_extensions
 */

#include <math.h>
#include "models.hh"
#include "parameters.hh"
#include <stdio.h>
using namespace std;

extern "C" {
	#include "libCylinder.h"
	#include "elliptical_cylinder.h"
}

EllipticalCylinderModel :: EllipticalCylinderModel() {
	scale      = Parameter(1.0);
	r_minor    = Parameter(20.0, true);
	r_minor.set_min(0.0);
	r_ratio    = Parameter(1.5, true);
	r_ratio.set_min(0.0);
	length     = Parameter(400.0, true);
	length.set_min(0.0);
	contrast   = Parameter(3.e-6);
	background = Parameter(0.0);
	cyl_theta  = Parameter(1.57, true);
	cyl_phi    = Parameter(0.0, true);
	cyl_psi    = Parameter(0.0, true);
}

/**
 * Function to evaluate 1D scattering function
 * The NIST IGOR library is used for the actual calculation.
 * @param q: q-value
 * @return: function value
 */
double EllipticalCylinderModel :: operator()(double q) {
	double dp[6];

	dp[0] = scale();
	dp[1] = r_minor();
	dp[2] = r_ratio();
	dp[3] = length();
	dp[4] = contrast();
	dp[5] = 0.0;

	// Get the dispersion points for the r_minor
	vector<WeightPoint> weights_rad;
	r_minor.get_weights(weights_rad);

	// Get the dispersion points for the r_ratio
	vector<WeightPoint> weights_rat;
	r_ratio.get_weights(weights_rat);

	// Get the dispersion points for the length
	vector<WeightPoint> weights_len;
	length.get_weights(weights_len);

	// Perform the computation, with all weight points
	double sum = 0.0;
	double norm = 0.0;

	// Loop over r_minor weight points
	for(int i=0; i<weights_rad.size(); i++) {
		dp[1] = weights_rad[i].value;

		// Loop over r_ratio weight points
		for(int j=0; j<weights_rat.size(); j++) {
			dp[2] = weights_rat[j].value;

			// Loop over length weight points
			for(int k=0; k<weights_len.size(); k++) {
				dp[3] = weights_len[k].value;

				sum += weights_rad[i].weight
					* weights_len[k].weight
					* weights_rat[j].weight
					* EllipCyl20(dp, q);
				norm += weights_rad[i].weight
				* weights_len[k].weight
				* weights_rat[j].weight;
			}
		}
	}
	return sum/norm + background();
}

/**
 * Function to evaluate 2D scattering function
 * @param q_x: value of Q along x
 * @param q_y: value of Q along y
 * @return: function value
 */
double EllipticalCylinderModel :: operator()(double qx, double qy) {
	EllipticalCylinderParameters dp;
	// Fill parameter array
	dp.scale      = scale();
	dp.r_minor    = r_minor();
	dp.r_ratio    = r_ratio();
	dp.length     = length();
	dp.contrast   = contrast();
	dp.background = 0.0;
	dp.cyl_theta  = cyl_theta();
	dp.cyl_phi    = cyl_phi();
	dp.cyl_psi    = cyl_psi();

	// Get the dispersion points for the r_minor
	vector<WeightPoint> weights_rad;
	r_minor.get_weights(weights_rad);

	// Get the dispersion points for the r_ratio
	vector<WeightPoint> weights_rat;
	r_ratio.get_weights(weights_rat);

	// Get the dispersion points for the length
	vector<WeightPoint> weights_len;
	length.get_weights(weights_len);

	// Get angular averaging for theta
	vector<WeightPoint> weights_theta;
	cyl_theta.get_weights(weights_theta);

	// Get angular averaging for phi
	vector<WeightPoint> weights_phi;
	cyl_phi.get_weights(weights_phi);

	// Get angular averaging for psi
	vector<WeightPoint> weights_psi;
	cyl_psi.get_weights(weights_psi);

	// Perform the computation, with all weight points
	double sum = 0.0;
	double norm = 0.0;

	// Loop over minor radius weight points
	for(int i=0; i<weights_rad.size(); i++) {
		dp.r_minor = weights_rad[i].value;


		// Loop over length weight points
		for(int j=0; j<weights_len.size(); j++) {
			dp.length = weights_len[j].value;

			// Loop over r_ration weight points
			for(int m=0; m<weights_rat.size(); m++) {
				dp.r_ratio = weights_rat[m].value;

			// Average over theta distribution
			for(int k=0; k<weights_theta.size(); k++) {
				dp.cyl_theta = weights_theta[k].value;

				// Average over phi distribution
				for(int l=0; l<weights_phi.size(); l++) {
					dp.cyl_phi = weights_phi[l].value;

				// Average over phi distribution
				for(int o=0; o<weights_psi.size(); o++) {
					dp.cyl_psi = weights_psi[o].value;

					double _ptvalue = weights_rad[i].weight
						* weights_len[j].weight
						* weights_rat[m].weight
						* weights_theta[k].weight
						* weights_phi[l].weight
						* weights_psi[o].weight
						* elliptical_cylinder_analytical_2DXY(&dp, qx, qy);
					if (weights_theta.size()>1) {
						_ptvalue *= sin(weights_theta[k].value);
					}
					sum += _ptvalue;

					norm += weights_rad[i].weight
						* weights_len[j].weight
						* weights_rat[m].weight
						* weights_theta[k].weight
						* weights_phi[l].weight
						* weights_psi[o].weight;

				}
				}
			}
			}
		}
	}
	// Averaging in theta needs an extra normalization
	// factor to account for the sin(theta) term in the
	// integration (see documentation).
	if (weights_theta.size()>1) norm = norm / asin(1.0);
	return sum/norm + background();
}

/**
 * Function to evaluate 2D scattering function
 * @param pars: parameters of the cylinder
 * @param q: q-value
 * @param phi: angle phi
 * @return: function value
 */
double EllipticalCylinderModel :: evaluate_rphi(double q, double phi) {
	double qx = q*cos(phi);
	double qy = q*sin(phi);
	return (*this).operator()(qx, qy);
}
/**
 * Function to calculate effective radius
 * @param pars: parameters of the sphere
 * @return: effective radius value
 */
double EllipticalCylinderModel :: calculate_ER() {
//NOT implemented yet!!!
}
