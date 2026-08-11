package eligibility

import (
	"driver-order-allocation-simulator/internal/model"
)

func IsEligible(driver model.Driver, order model.Order, mode string) bool {
	if !driver.Online {
		return false
	}
	if driver.AccountStatus != "active" {
		return false
	}

	supportsService := false
	for _, svc := range driver.ServiceTypes {
		if svc == order.ServiceType {
			supportsService = true
			break
		}
	}
	if !supportsService {
		return false
	}

	if mode == "hard" && driver.DeviceStatus != "healthy" {
		return false
	}

	return true
}

func FilterEligible(drivers []model.Driver, order model.Order, mode string) []model.Driver {
	var result []model.Driver
	for _, d := range drivers {
		if IsEligible(d, order, mode) {
			result = append(result, d)
		}
	}
	return result
}
